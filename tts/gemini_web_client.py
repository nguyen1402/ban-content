# -*- coding: utf-8 -*-
"""Gọi Gemini WEB (gemini.google.com) bằng COOKIE thay cho khoá API.

Vì sao: đường khoá API (generativelanguage.googleapis.com) có trần RPM/RPD cứng nên
lượt dịch dài luôn ăn 429, và hay gặp 503 lúc Google quá tải. Tài khoản Gemini web
tính hạn mức theo NGƯỜI DÙNG (như khi ngồi gõ tay trên trình duyệt), nên đây là một
"nhà cung cấp" khác hẳn — cạn bên này không kéo theo bên kia.

Kiến trúc:

    gemini_cookie_ext/ (tiện ích Chrome)  ->  gemini_cookie_store.py (kho cookie)
                                          ->  FILE NÀY  ->  srt_translate_core.py

Phần nói chuyện với Gemini web dùng thư viện ``gemini_webapi`` (bên thứ ba, được cập
nhật liên tục). KHÔNG tự chép giao thức nội bộ của Google vào đây: gói request là một
mảng 81 ô có đánh số, kèm header chọn model và bộ đọc khung stream — Google đổi là
gãy, mà thư viện kia vá theo. Ở đây chỉ giữ phần của riêng app:

  * đọc cookie từ kho (tiện ích đẩy sang, luôn mới),
  * chạy thư viện bất đồng bộ trong MỘT vòng lặp nền để phần còn lại của app gọi
    theo lối đồng bộ như mọi provider khác,
  * dịch lỗi của thư viện sang loại lỗi mà bộ điều phối key/model hiểu (hết hạn mức
    -> xoay tài khoản; cookie hỏng -> báo người dùng lấy lại; lỗi tạm -> thử lại).

Hạn chế đã biết, ghi rõ để khỏi kỳ vọng nhầm:
  * KHÔNG có tham số nhiệt độ (temperature) — web không cho chỉnh; tham số nhận vào
    chỉ để trùng chữ ký với các provider khác.
  * Mỗi tài khoản chạy TUẦN TỰ: lô sau chỉ gửi khi lô trước đã xong (hàng đợi trong
    ``_xep_hang``). Muốn nhanh hơn thì thêm TÀI KHOẢN, đừng nới số lượt song song.
  * Đây là cửa dành cho người dùng cuối, không phải API chính thức. Google có thể
    đổi giao thức bất cứ lúc nào, và dùng quá đà thì tài khoản có thể bị hạn chế.
"""

import asyncio
import concurrent.futures
import copy
import os
import re
import threading
import time

import gemini_cookie_store as store

try:
    from curl_cffi import CurlOpt as _CurlOpt
except Exception:                                      # noqa: BLE001 - thư viện mềm
    _CurlOpt = None

# --------------------------------------------------------------------------- #
#  Nạp thư viện (mềm): thiếu thì báo bằng lỗi có hướng dẫn, không làm chết app.
# --------------------------------------------------------------------------- #
try:
    import gemini_webapi as _gwa
    from gemini_webapi import GeminiClient as _GeminiClient
    _IMPORT_ERR = None
except Exception as e:                                   # noqa: BLE001
    _gwa = None
    _GeminiClient = None
    _IMPORT_ERR = e

# Thư viện in 4-5 dòng INFO/WARNING mỗi lần mở phiên CHO TỪNG tài khoản ("Account quota
# updated", "abuse status", "client initialized", "UNAUTHENTICATED"/"RPC … failed" với
# cookie hết hạn) — tiền kiểm 8 tài khoản là ~40 dòng tiếng Anh màu mè đầu mỗi lượt review,
# đọc như hàng loạt lỗi dù lượt chạy vẫn ổn (người dùng 06/10/2026: "gemini hay bị đẻ ra
# lỗi"). App đã tự báo mọi thứ đáng biết bằng tiếng Việt (tiền kiểm, hết hạn, đổi model),
# nên chỉ giữ dòng ERROR. Muốn soi lại: đặt GEMINI_WEB_LOG_LEVEL=INFO.
if _gwa is not None and hasattr(_gwa, "set_log_level"):
    try:
        _gwa.set_log_level(os.environ.get("GEMINI_WEB_LOG_LEVEL") or "ERROR")
    except Exception:                                    # noqa: BLE001
        pass

CAI_DAT = "pip install gemini_webapi"

# Số lượt gọi chạy cùng lúc trên MỖI tài khoản. MẶC ĐỊNH 1 = gửi lô sau chỉ khi lô
# trước đã xong, đúng như ngồi gõ tay trên trình duyệt.
#
# Đo 21/08/2026 thì 2 lượt/lúc nhanh gấp đôi và không hỏng thêm, NHƯNG số đo đó chỉ nói
# về tốc độ, không nói gì về việc tài khoản Google có bị đánh dấu bất thường hay không —
# mà cái giá của việc bị khoá tài khoản thì lớn hơn nhiều lần vài chục giây tiết kiệm
# được. Người dùng chốt chạy tuần tự; muốn nhanh thì THÊM TÀI KHOẢN (mỗi tài khoản một
# làn riêng), đừng nới số này.
CONCURRENCY = int(os.environ.get("GEMINI_WEB_CONCURRENCY") or 1)

# Chờ tối đa cho một lượt gọi (giây) nếu bên gọi không nói gì.
TIMEOUT_MAC_DINH = 300

# Hàng đợi phiên chỉ là lớp an toàn thứ hai; pool phía trên vốn đã bảo đảm một request
# trên mỗi tài khoản. Chờ 30 phút ở đây chỉ che mất socket/sem bị kẹt.
SESSION_QUEUE_TIMEOUT = max(
    30, int(os.environ.get("GEMINI_WEB_SESSION_QUEUE_TIMEOUT") or 180))


class GeminiWebError(RuntimeError):
    """Lỗi tạm — cứ thử lại/đổi tài khoản."""


class GeminiWebTimeout(GeminiWebError):
    """Một lô vượt deadline: hủy request, bỏ phiên và chuyển nguyên lô sang cookie khác."""


class GeminiWebAuth(GeminiWebError):
    """Cookie hỏng/hết hạn — phải mở tiện ích lấy lại cookie."""


class GeminiWebQuota(GeminiWebError):
    """Tài khoản này cạn hạn mức — xoay sang tài khoản khác."""


class GeminiWebBlocked(GeminiWebError):
    """Google chặn tạm (IP/tài khoản) — dừng, đừng nện tiếp."""


class GeminiWebMissing(GeminiWebError):
    """Chưa cài thư viện gemini_webapi."""


class GeminiWebFlaky(GeminiWebError):
    """Web trả 200 nhưng nội dung không dùng được (câu lỗi soạn sẵn, hoặc rỗng).

    Gọi lại là được, nên KHÔNG để nó chui lên bộ điều phối: ở trên đó mọi 'lỗi tạm' đều
    bị phạt cho key nghỉ ~70 giây — luật đúng cho 429 theo phút của API, nhưng với đường
    cookie chỉ có 1-2 tài khoản thì 70 giây đó là 70 giây ngồi không. Đo 21/08/2026: một
    lượt dịch 300 câu mất 285,9 giây thì 150 giây là tiền phạt kiểu này, trong khi lượt
    chạy sạch chỉ hết ~60 giây.

    cho: số giây chờ CƠ SỞ trước khi gọi lại (nhân theo số lần thử)."""

    def __init__(self, msg="", cho=2.0):
        super().__init__(msg)
        self.cho = cho


class GeminiWebStopped(Exception):
    """Người dùng bấm Dừng."""


# Câu lỗi soạn sẵn của giao diện Gemini: HTTP vẫn 200, chữ vẫn về, nhưng nội dung là
# thông báo hỏng chứ không phải bản dịch. ĐO 20/08/2026 trên 10 lô dịch thật (100 câu
# tiếng Trung/lô): 1 lô dính, và ĐÚNG lô đó gọi lại 4/4 lần đều ra đủ 100 câu -> hỏng
# vặt ngẫu nhiên, không phải do nội dung. Nếu không bắt ở đây, nó chui xuống bộ đọc JSON
# rồi vỡ thành lỗi 'Response không phải JSON array' — đọc log không ai hiểu vì sao.
#
# CHỈ thêm mẫu ĐÃ THẤY THẬT vào danh sách này. Nhét cả câu từ chối ('I can't help with
# that') vào đây là sai: từ chối thì gọi lại vẫn từ chối, chỉ tổ đốt thêm lượt.
#
# Đã thấy hai biến thể chỉ trong 18 lô đo: "I seem to be encountering an error…" và
# "I encountered an error doing what you asked…" — cùng một ý, khác cách nói, nên bắt
# theo MẪU chứ không so chuỗi cứng.
_LOI_SOAN_SAN = (
    r"i (?:seem to be encountering|encountered|ran into|am encountering)\s+an error",
    r"i'?m having trouble",
    r"something went wrong",
    r"tôi (?:dường như )?(?:đang |đã )?gặp (?:phải )?lỗi",
)
# Bản dịch một lô dài vài nghìn ký tự, còn câu lỗi thì ngắn — chặn theo độ dài để câu
# trả lời thật có nhắc tới mấy chữ đó cũng không bị bắt oan.
_NGUONG_NGAN = 400


def _la_loi_soan_san(raw):
    if not raw or len(raw) > _NGUONG_NGAN:
        return False
    t = raw.lower()
    return any(re.search(m, t) for m in _LOI_SOAN_SAN)


def available():
    """(dùng được?, lý do nếu không). Gọi trước khi bật chế độ cookie trong giao diện."""
    if _gwa is None:
        return False, ("Chưa cài thư viện gemini_webapi (%s). Chạy: %s"
                       % (type(_IMPORT_ERR).__name__, CAI_DAT))
    return True, ""


# --------------------------------------------------------------------------- #
#  Vòng lặp bất đồng bộ chạy nền — cả app chỉ có MỘT
# --------------------------------------------------------------------------- #
_LOOP = None
_LOOP_LOCK = threading.Lock()


def _loop():
    global _LOOP
    with _LOOP_LOCK:
        if _LOOP is None or _LOOP.is_closed():
            _LOOP = asyncio.new_event_loop()
            threading.Thread(target=_LOOP.run_forever, daemon=True,
                             name="gemini-web-loop").start()
        return _LOOP


def _chay(coro, timeout, stop_event=None):
    """Chạy coroutine với deadline thật; hết giờ thì cancel ngay, không chờ thêm."""
    fut = asyncio.run_coroutine_threadsafe(coro, _loop())
    seconds = max(0.05, float(timeout or TIMEOUT_MAC_DINH))
    han = time.monotonic() + seconds
    while True:
        con = han - time.monotonic()
        if con <= 0:
            fut.cancel()
            raise GeminiWebTimeout(
                "quá hạn %ss (Gemini web không trả lời)" % int(round(seconds)))
        try:
            return fut.result(min(0.5, con))
        except concurrent.futures.TimeoutError:
            if stop_event is not None and stop_event.is_set():
                fut.cancel()
                raise GeminiWebStopped()


# --------------------------------------------------------------------------- #
#  Phiên theo TÀI KHOẢN
# --------------------------------------------------------------------------- #
class _Phien:
    # 'models' giữ NGUYÊN nghĩa cũ (danh sách TÊN model) vì nhiều chỗ đang đọc nó.
    # 'model_info' là bản đầy đủ của cùng danh sách đó — có mã model (duy nhất), tên
    # hiện trên web và mô tả — để ô chọn model trong giao diện ghim đúng MỘT mục thay
    # vì đoán theo từ khoá flash/lite/pro.
    __slots__ = ("client", "van_tay", "tao_luc", "sem", "models", "model_info",
                 "trang_thai", "dau_ts")

    def __init__(self, client, van_tay, sem):
        self.client = client
        self.van_tay = van_tay
        self.tao_luc = time.time()
        self.sem = sem
        self.models = []
        self.model_info = []
        self.trang_thai = ""
        self.dau_ts = ""


_PHIEN = {}
_PHIEN_LOCK = threading.Lock()
_PHIEN_BUILD_LOCKS = {}

# Kết quả tiền kiểm dùng lại trong một khoảng ngắn nếu kho cookie không đổi. Nhờ đó
# người dùng bấm "Kiểm tra tất cả" rồi Dịch, hoặc một loạt Tự động có nhiều video,
# không phải gửi lại câu thử cho mọi tài khoản ở từng video.
PREFLIGHT_CACHE_SECONDS = 30 * 60
_PREFLIGHT_LOCK = threading.Lock()
_PREFLIGHT_CACHE = {}
_PREFLIGHT_INFLIGHT = {}


def _van_tay(cookies):
    """Dấu nhận biết bộ cookie — đổi nghĩa là người dùng đăng nhập lại/đổi tài khoản."""
    return (cookies.get("__Secure-1PSID") or "")[-24:]


def _dau_ts(cookies):
    """Dấu của __Secure-1PSIDTS — cookie Google XOAY ~10 phút/lần, tiện ích đẩy lại mỗi
    lần đổi. KHÔNG dùng làm vân tay phiên (đổi liên tục thì phiên nào cũng phải dựng
    lại, mất ~3 giây mỗi lần), chỉ để biết 'kho đã có cookie mới hơn phiên này'."""
    return (cookies.get("__Secure-1PSIDTS") or "")[-24:]


# Phiên đã chết mà cookie trong kho KHÔNG đổi: bao lâu mới được thử dựng lại.
THU_LAI_PHIEN_CHET = 60.0


def _phien_chet_can_dung_lai(p, cookies):
    """Phiên ĐÃ CHẾT vì chưa đăng nhập được, mà kho nay có cookie mới hơn -> dựng lại.

    Vì sao cần: __Secure-1PSID KHÔNG đổi khi Google chỉ xoay __Secure-1PSIDTS, nên vân
    tay phiên vẫn khớp và phiên chết được dùng lại mãi. Hậu quả thấy được (04/09/2026):
    người dùng bấm 'Gửi vào app' lấy cookie mới, tiện ích báo 'Đã đăng nhập — 18 cookie',
    mà app vẫn trả 'cookie hết hạn (UNAUTHENTICATED)' cho tới khi tắt app mở lại — vì
    nó vẫn cầm phiên chết dựng từ cookie cũ. Thư viện cũng không tự chữa được: nó DỪNG
    vòng tự làm mới cookie ngay khi tài khoản không ở trạng thái dùng được.

    Chỉ dựng lại khi phiên ĐÃ chết: phiên đang sống mà cookie xoay thì cứ để yên.

    08/09/2026 — nới thêm: cookie KHÔNG đổi thì cũng phải thử lại sau THU_LAI_PHIEN_CHET
    giây. Vì sao: bản cũ chỉ dựng lại khi kho có cookie MỚI, nên phiên chết mà người dùng
    không bấm 'Gửi vào app' thì chết tới hết lượt — đo trên phim 7681503080570948633
    (log 19:17): cả 7 tài khoản báo UNAUTHENTICATED từ dòng đầu tới gần dòng cuối, người
    dùng phải vào bấm tay từng cookie. Dựng lại KHÔNG cần cookie mới vẫn cứu được, vì
    _tao_client gọi cli.init() — bước đó tự xin __Secure-1PSIDTS mới bằng __Secure-1PSID
    đang có, và bật lại vòng auto_refresh mà thư viện đã tắt khi tài khoản hỏng.

    Quãng nghỉ để không dựng lại liên tục: mỗi lần dựng tốn ~3s, và phiên mới mang
    tao_luc mới nên tự giãn ra. 1PSID chết hẳn thì cũng chỉ tốn ~3s mỗi phút mỗi tài
    khoản, đổi lại lượt dịch tự hồi phục thay vì hỏng cả phim."""
    if getattr(p, "trang_thai", "") != "UNAUTHENTICATED":
        return False
    if getattr(p, "dau_ts", "") != _dau_ts(cookies):
        return True
    tao_luc = float(getattr(p, "tao_luc", 0.0) or 0.0)
    return (time.time() - tao_luc) >= THU_LAI_PHIEN_CHET


def _doc_cookie(acc_id):
    rec = store.get_account(acc_id)
    if not rec:
        co = ", ".join(a["id"] for a in store.list_accounts()) or "(kho rỗng)"
        raise GeminiWebAuth("Không có tài khoản cookie '%s'. Đang có: %s" % (acc_id, co))
    ck = rec.get("cookies") or {}
    if not ck.get("__Secure-1PSID"):
        raise GeminiWebAuth("Tài khoản '%s' thiếu __Secure-1PSID — hãy đăng nhập lại "
                            "gemini.google.com rồi bấm 'Gửi vào app'." % acc_id)
    return ck


def _cau_hinh_transport(cli):
    """Không giữ keep-alive chết trong curl_cffi suốt một phim dài.

    Gemini web gửi thêm RPC hoạt động trước mỗi lô. Trên Windows, phía Google đóng các
    HTTP/2 connection cũ nhưng curl_cffi 0.16 có thể giữ socket ở CLOSE_WAIT tới tận lúc
    AsyncSession.close(). FORBID_REUSE làm libcurl chủ động đóng socket ngay sau response.
    TLS mở lại ở request kế tiếp tốn rất ít so với một lô dịch 10–120 giây.
    """
    session = getattr(cli, "client", None)
    options = getattr(session, "curl_options", None)
    if _CurlOpt is not None and options is not None:
        options[_CurlOpt.FORBID_REUSE] = 1
        options[_CurlOpt.TCP_KEEPALIVE] = 1


async def _tao_client(cookies, timeout):
    cli = _GeminiClient(cookies.get("__Secure-1PSID"), cookies.get("__Secure-1PSIDTS"))
    try:
        # Đưa nốt cookie khác của phiên (SID/HSID/SAPISID/NID…).
        them = {k: v for k, v in cookies.items()
                if k not in ("__Secure-1PSID", "__Secure-1PSIDTS")}
        if them:
            cli.cookies = them
        await cli.init(timeout=timeout, auto_close=False, auto_refresh=True,
                       refresh_interval=600, verbose=False)

        # generate_content tự sync hoạt động; hủy watchdog activity thừa, giữ refresh cookie.
        activity = getattr(cli, "activity_task", None)
        if activity is not None:
            activity.cancel()
            await asyncio.gather(activity, return_exceptions=True)
            cli.activity_task = None

        _cau_hinh_transport(cli)
        return cli
    except BaseException:
        # Deadline có thể cắt giữa init; client nửa sống cũng phải được thu transport.
        try:
            await _dong_client_sach(cli)
        except BaseException:
            pass
        raise


async def _dong_client_sach(cli):
    """Hủy/đợi background task rồi đóng cả AsyncSession, kể cả close() lỗi nửa chừng."""
    current = asyncio.current_task()
    tasks = [
        task for task in (
            getattr(cli, "close_task", None),
            getattr(cli, "refresh_task", None),
            getattr(cli, "activity_task", None),
        )
        if task is not None and task is not current
    ]
    raw_session = getattr(cli, "client", None)
    try:
        await cli.close()
    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        # Bản thư viện nào close() văng lỗi trước khi tới AsyncSession.close() thì wrapper
        # vẫn phải thu transport; nếu không các socket CLOSE_WAIT sống tới lúc tắt app.
        if raw_session is not None and getattr(cli, "client", None) is not None:
            try:
                await raw_session.close()
            finally:
                cli.client = None


def _dong_phien(p, timeout=10):
    if p is None or getattr(p, "client", None) is None:
        return True
    try:
        _chay(_dong_client_sach(p.client), timeout)
        return True
    except Exception:                                   # noqa: BLE001 - cleanup tốt nhất
        return False


def _loai_phien(acc_id, expected=None, timeout=10, background=False):
    """Rút phiên ngay; timeout thì đóng transport nền để không cộng thêm 10s vào deadline."""
    with _PHIEN_LOCK:
        current = _PHIEN.get(acc_id)
        if current is None or (expected is not None and current is not expected):
            return False
        _PHIEN.pop(acc_id, None)
    if background:
        threading.Thread(
            target=_dong_phien, args=(current,), kwargs={"timeout": timeout},
            daemon=True, name="gemini-web-close-%s" % acc_id,
        ).start()
    else:
        _dong_phien(current, timeout=timeout)
    return True


def _build_lock(acc_id):
    with _PHIEN_LOCK:
        return _PHIEN_BUILD_LOCKS.setdefault(acc_id, threading.Lock())


def _phien(acc_id, timeout=TIMEOUT_MAC_DINH, lam_moi=False):
    """Lấy/dựng phiên trong deadline; khóa dựng chỉ thuộc đúng tài khoản này."""
    ok, vi_sao = available()
    if not ok:
        raise GeminiWebMissing(vi_sao)

    seconds = max(0.05, float(timeout or TIMEOUT_MAC_DINH))
    deadline = time.monotonic() + seconds

    def con_lai():
        con = deadline - time.monotonic()
        if con <= 0:
            raise GeminiWebTimeout(
                "quá hạn %ss khi dựng phiên '%s'" % (int(round(seconds)), acc_id))
        return con

    # Một phiên cũ đang dựng cũng phải chịu cùng deadline của lô.
    build_lock = _build_lock(acc_id)
    if not build_lock.acquire(timeout=con_lai()):
        raise GeminiWebTimeout(
            "quá hạn %ss khi chờ dựng phiên '%s'" % (int(round(seconds)), acc_id))
    try:
        cookies = _doc_cookie(acc_id)
        vt = _van_tay(cookies)
        with _PHIEN_LOCK:
            p = _PHIEN.get(acc_id)
            if (p is not None and not lam_moi and p.van_tay == vt
                    and not _phien_chet_can_dung_lai(p, cookies)):
                return p
            if p is not None:
                _PHIEN.pop(acc_id, None)

        if p is not None:
            _dong_phien(p, timeout=min(10.0, con_lai()))

        remaining = con_lai()
        cli = _chay(_tao_client(cookies, remaining), remaining)
        p = _Phien(cli, vt, threading.Semaphore(max(1, CONCURRENCY)))
        try:
            ds = cli.list_models() or []
            p.models = [m.model_name for m in ds]
            p.model_info = [_ta_model(m) for m in ds]
        except Exception:
            p.models = []
            p.model_info = []
        p.trang_thai = _ten_trang_thai(cli)
        p.dau_ts = _dau_ts(cookies)
        with _PHIEN_LOCK:
            _PHIEN[acc_id] = p
        return p
    finally:
        build_lock.release()


def _xep_hang(sem, timeout, stop_event, han_cho=SESSION_QUEUE_TIMEOUT, on_wait=None):
    """Chờ phiên có trần + heartbeat; không còn khoảng im lặng 30 phút."""
    # Đây là trần trên: lô 40s không được chờ semaphore 180s.
    limit = max(0.05, min(float(timeout or TIMEOUT_MAC_DINH), float(han_cho)))
    started = time.time()
    het = started + limit
    next_notice = started + 15.0
    while time.time() < het:
        if stop_event is not None and stop_event.is_set():
            raise GeminiWebStopped()
        con = max(0.0, het - time.time())
        if sem.acquire(timeout=min(0.5, con)):
            return True
        now = time.time()
        if on_wait is not None and now >= next_notice:
            try:
                on_wait(now - started, limit)
            except Exception:
                pass
            next_notice = now + 15.0
    return False


def _ten_trang_thai(cli):
    """Tên trạng thái tài khoản do thư viện đọc được ('AVAILABLE', 'UNAUTHENTICATED'…).

    Vì sao cần: cookie hết hạn KHÔNG làm init() ném lỗi — thư viện vẫn dựng xong phiên
    và vẫn trả về một danh sách model, nhưng đó là danh sách của KHÁCH (chưa đăng nhập),
    không phải của tài khoản. Đo 04/09/2026: phiên hết hạn trả đúng 3 mục
    (3.5 Flash-Lite / 3.6 Flash / 3.1 Pro) trong khi tài khoản thật có nhiều hơn. Không
    có cờ này thì ô chọn model sẽ mời người dùng ghim nhầm model của khách."""
    try:
        return getattr(getattr(cli, "account_status", None), "name", "") or ""
    except Exception:                                    # noqa: BLE001
        return ""


def _ta_model(m):
    """Một mục model của thư viện -> dict thuần để đưa qua luồng/giao diện.

    'id' là mã hex DUY NHẤT của mục. Tên (`model_name`) thì KHÔNG duy nhất: web đặt
    cùng một tên cho nhiều mức suy nghĩ của cùng dòng model (Nhanh / Cân bằng / Kỹ
    nhất), nên chỉ ghim theo tên là bốc nhầm mục. Thư viện nhận thẳng mã hex ở tham số
    ``model=`` nên ghim theo 'id' là chắc nhất."""
    ten = str(getattr(m, "model_name", "") or "")
    hien = str(getattr(m, "display_name", "") or "")
    mo_ta = str(getattr(m, "description", "") or "")
    return {
        "id": str(getattr(m, "model_id", "") or ""),
        "name": ten,
        "display": hien,
        "desc": mo_ta,
        "available": bool(getattr(m, "is_available", True)),
        "advanced": bool(getattr(m, "advanced_only", False)),
        "nhan": nhan_model(hien or ten, mo_ta),
    }


def nhan_model(hien, mo_ta=""):
    """Chữ hiện trong ô chọn model. Kèm mô tả vì mấy mức suy nghĩ của cùng một dòng
    model trùng tên hiển thị — bỏ mô tả đi thì ba dòng giống hệt nhau."""
    hien = " ".join(str(hien or "").split())
    mo_ta = " ".join(str(mo_ta or "").split())
    if mo_ta and mo_ta.lower() != hien.lower():
        return "%s — %s" % (hien, mo_ta[:60])
    return hien


def _model_info_cua(p):
    """Đọc model_info của phiên mà không tin phiên là đồ thật (test cắm mock vào)."""
    try:
        ds = list(getattr(p, "model_info", None) or [])
    except Exception:                                    # noqa: BLE001
        return []
    return [x for x in ds if isinstance(x, dict)]


def list_model_info(account_id, timeout=90, lam_moi=False):
    """Danh sách model THẬT của một tài khoản cookie, KHÔNG tốn lượt sinh nội dung.

    Khác ``check()``: chỗ này chỉ dựng/lấy lại phiên rồi đọc danh sách model mà thư
    viện đã nhận lúc init — không gửi câu hỏi nào lên Gemini. Nhờ vậy nút 'Nạp model'
    trong giao diện bấm bao nhiêu lần cũng không ăn vào hạn mức tài khoản.

    Trả dict: ok / kind / msg / models (dict đầy đủ) / trang_thai.
    """
    ok, vi_sao = available()
    if not ok:
        return {"ok": False, "kind": "missing", "msg": vi_sao, "models": [],
                "trang_thai": ""}
    try:
        p = _phien(account_id, timeout=timeout, lam_moi=lam_moi)
    except Exception as e:                               # noqa: BLE001
        return dict(_check_error_result(e), trang_thai="")
    trang_thai = str(getattr(p, "trang_thai", "") or "")
    ds = _model_info_cua(p)
    if trang_thai == "UNAUTHENTICATED":
        # Danh sách lúc này là của KHÁCH, không phải của tài khoản — trả về nhưng nói
        # rõ là không dùng để ghim được.
        return {"ok": False, "kind": "auth", "trang_thai": trang_thai, "models": ds,
                "msg": ("cookie hết hạn (%s) — danh sách này là của phiên CHƯA ĐĂNG "
                        "NHẬP. Mở tiện ích Chrome bấm 'Gửi vào app' rồi nạp lại."
                        % trang_thai)}
    if not ds:
        return {"ok": False, "kind": "error", "trang_thai": trang_thai, "models": [],
                "msg": "phiên không trả về danh sách model nào"}
    return {"ok": True, "kind": "ok", "trang_thai": trang_thai, "models": ds,
            "msg": "%d model" % len(ds)}


def _tim_model_ghim(p, ten):
    """Tìm ĐÚNG mục model người dùng đã ghim (mã hex / tên hiện / nhãn trong ô chọn).

    Trả về mã hex của mục — thư viện nhận mã hex ở ``model=`` và khớp trước mọi kiểu
    tên khác, nên không sợ trùng tên giữa các mức suy nghĩ."""
    t = (ten or "").strip().lower()
    if not t:
        return None
    ds = _model_info_cua(p)
    for m in ds:
        if (m.get("id") or "").lower() == t:
            return m.get("id")
    for m in ds:
        if (m.get("display") or "").strip().lower() == t or (m.get("nhan") or "").strip().lower() == t:
            return m.get("id") or m.get("name")
    return None


def _chon_model(p, ten):
    """Đổi tên model kiểu API ('gemini-3.1-flash-lite') sang model CÓ THẬT của tài khoản.

    Web đặt tên khác API và mỗi tài khoản một danh sách (tuỳ gói), nên không ghim cứng
    được: chỉ soi từ khoá lite/pro/flash trong danh sách tài khoản đang có. Không khớp
    -> None = để nguyên model mặc định của tài khoản."""
    ghim = _tim_model_ghim(p, ten)
    if ghim:
        # Người dùng đã chọn đúng một mục trong danh sách THẬT của tài khoản: dùng
        # nguyên mục đó, không cho bước đoán từ khoá bên dưới đổi ý.
        return ghim
    ten = (ten or "").lower()
    ds = p.models or []
    if not ds:
        return None
    if ten in [m.lower() for m in ds]:
        return next(m for m in ds if m.lower() == ten)
    if "lite" in ten:
        uu_tien = ("lite",)
    elif "pro" in ten:
        uu_tien = ("pro",)
    else:
        # Xin Flash mà tài khoản KHÔNG có Flash: thà LÊN Pro còn hơn TỤT xuống
        # Flash-Lite (người dùng chốt 08/09/2026 — lite dịch kém hơn hẳn). Lite vẫn là
        # chỗ dựa cuối, nằm ở vòng 'tranh_lite=False' bên dưới, nên tài khoản chỉ có
        # mỗi lite thì vẫn chạy được y như trước.
        # Pro KHÔNG bao giờ cướp chỗ của Flash: vòng lặp duyệt HẾT 'flash' trên cả
        # danh sách rồi mới sang 'pro'. Đáng lưu ý vì Pro đắt hơn nhiều — theo đo
        # 04/09/2026: Lite 0 credit, Flash 2-6, Pro ~100 (hạn free 600 credit/5 giờ).
        uu_tien = ("flash", "pro")
    # 'flash' nằm TRONG 'flash-lite', mà tài khoản trả danh sách theo thứ tự
    # Flash-Lite trước Flash (đo 04/09/2026) — quét thẳng là xin flash được đưa
    # flash-lite, tức bị hạ cấp mà không ai biết. Nên quét hai vòng: vòng đầu bỏ qua
    # bản lite, hết cách mới nhận (tài khoản chỉ có mỗi flash-lite thì vẫn có model
    # để chạy, y như trước).
    bo_lite = "lite" not in uu_tien
    for tranh_lite in ((True, False) if bo_lite else (False,)):
        for tu in uu_tien:
            for m in ds:
                ml = m.lower()
                if tranh_lite and "lite" in ml:
                    continue
                # Bỏ qua bản '-plus/-advanced' nếu có bản thường: chúng ăn vào hạn mức
                # gói trả phí, cạn nhanh hơn nhiều.
                if tu in ml and "plus" not in ml and "advanced" not in ml:
                    return m
        for tu in uu_tien:
            for m in ds:
                ml = m.lower()
                if tranh_lite and "lite" in ml:
                    continue
                if tu in ml:
                    return m
    return None


def _dich_loi(e):
    """Lỗi của thư viện -> lỗi của app (bộ điều phối đọc loại lỗi để quyết định)."""
    ten = type(e).__name__
    thong = str(e)
    if _gwa is not None:
        if isinstance(e, getattr(_gwa, "UsageLimitExceededError", ())):
            return GeminiWebQuota("hết hạn mức tài khoản: " + thong[:200])
        if isinstance(e, getattr(_gwa, "TemporarilyBlockedError", ())):
            return GeminiWebBlocked("Google chặn tạm: " + thong[:200])
        if isinstance(e, getattr(_gwa, "AuthError", ())):
            return GeminiWebAuth("cookie hỏng/hết hạn: " + thong[:200])
        if isinstance(e, getattr(_gwa, "ModelInvalidError", ())):
            return GeminiWebError("model không dùng được: " + thong[:200])
    low = thong.lower()
    # Cookie hết hạn hiện ra dưới cái tên chẳng liên quan: thư viện báo
    # "gemini-flash is not available for use. Account status: UNAUTHENTICATED" — đọc log
    # thì tưởng model bị gỡ, hoá ra chỉ là __Secure-1PSIDTS đã cũ (Google xoay ~10
    # phút/lần). Gọi đúng tên để người dùng biết phải bấm 'Gửi vào app' lần nữa.
    if ("unauthenticated" in low or "account status" in low
            or "check your cookies" in low or "1016" in low):
        return GeminiWebAuth("cookie đã hết hạn — mở tiện ích Chrome rồi bấm "
                             "'Gửi vào app' (%s)" % thong[:120])
    if "1037" in thong or "usage limit" in thong.lower():
        return GeminiWebQuota(thong[:200])
    if "SNlM0e" in thong or "auth" in ten.lower() or "cookie" in thong.lower():
        return GeminiWebAuth(thong[:200])
    return GeminiWebError("%s: %s" % (ten, thong[:200]))


_DA_BAO_MODEL = set()


def _bao_model(p, account_id, xin, thuc, on_log):
    """Nói MỘT lần cho mỗi (tài khoản, model) rằng lô đang chạy bằng model nào.

    Vì sao cần: tên người dùng gõ chỉ là gợi ý, app tự soi trong danh sách thật của tài
    khoản — không in ra thì không có cách nào biết mục đã ghim có thật sự được dùng hay
    đã bị bước đoán từ khoá đổi sang model khác."""
    if on_log is None:
        return
    khoa = (account_id, str(xin), str(thuc))
    if khoa in _DA_BAO_MODEL:
        return
    _DA_BAO_MODEL.add(khoa)
    nhan = ""
    for m in _model_info_cua(p):
        if thuc and thuc in (m.get("id"), m.get("name"), m.get("display")):
            nhan = m.get("nhan") or ""
            break
    try:
        on_log("    [gemini-web] %s dùng model: %s%s"
               % (account_id, nhan or thuc or "(mặc định của tài khoản)",
                  "" if not nhan else " [%s]" % thuc))
    except Exception:                                    # noqa: BLE001
        pass


async def _hoi(cli, prompt, model, temporary, files=None):
    # files (27/09/2026): Gemini web NHẬN ẢNH/VIDEO — đo: 12 khung rời hoặc 1 ảnh lưới
    # 4x3 đều mô tả đúng 12/12. Bỏ trống -> y như cũ.
    if files:
        out = await cli.generate_content(prompt, files=list(files), model=model,
                                         temporary=temporary)
    else:
        out = await cli.generate_content(prompt, model=model, temporary=temporary)
    return (getattr(out, "text", "") or "").strip()


def ask(account_id, prompt, model=None, timeout=TIMEOUT_MAC_DINH, retries=3,
        stop_event=None, on_log=None, temporary=True, files=None):
    """Hỏi Gemini web 1 lượt, trả về CHỮ. Ném GeminiWeb* khi hỏng.

    temporary=True: dùng "trò chuyện tạm" — không lưu vào lịch sử tài khoản và không
    dính ngữ cảnh của lượt trước, đúng thứ bộ dịch cần (mỗi lô là một lệnh độc lập)."""
    if stop_event is not None and stop_event.is_set():
        raise GeminiWebStopped()
    loi_cuoi = None
    lam_moi = False
    p = None
    seconds = max(0.05, float(timeout or TIMEOUT_MAC_DINH))
    deadline = time.monotonic() + seconds

    def con_lai():
        con = deadline - time.monotonic()
        if con <= 0:
            raise GeminiWebTimeout(
                "quá hạn %ss cho nguyên lô của '%s'" % (int(round(seconds)), account_id))
        return con

    for lan in range(1, max(1, int(retries)) + 1):
        if stop_event is not None and stop_event.is_set():
            raise GeminiWebStopped()
        try:
            p = _phien(account_id, timeout=con_lai(), lam_moi=lam_moi)
            ten_model = _chon_model(p, model)
            _bao_model(p, account_id, model, ten_model, on_log)
            # Xếp hàng chờ tới lượt. Vì chạy tuần tự nên nhiều lô có thể cùng đợi
            # một tài khoản: hạn chờ phải tính theo CẢ HÀNG (mỗi lô ~10-15 giây) chứ
            # không phải theo một lượt gọi, kẻo lô đứng cuối bị đá ra oan.
            remaining = con_lai()
            if not _xep_hang(
                    p.sem, remaining, stop_event, han_cho=remaining,
                    on_wait=(lambda elapsed, limit:
                             on_log("    [gemini-web] tài khoản '%s' vẫn bận %.0fs/%.0fs…"
                                    % (account_id, elapsed, limit))
                             if on_log else None)):
                raise GeminiWebTimeout(
                    "chờ quá deadline %ss tới lượt tài khoản '%s' — loại phiên kẹt"
                    % (int(round(seconds)), account_id))
            try:
                # Chỉ truyền 'files' khi CÓ ảnh: lời gọi chữ thuần giữ nguyên hình dạng cũ.
                hoi = (_hoi(p.client, prompt, ten_model, temporary, files) if files
                       else _hoi(p.client, prompt, ten_model, temporary))
                raw = _chay(hoi, con_lai(), stop_event)
            finally:
                p.sem.release()
            if not raw:
                # Rỗng thường là dấu hiệu Google HÃM TỐC sau một loạt lượt gọi dồn dập
                # (đo: chỉ xuất hiện sau ~20 lượt trong vài phút, gọi thưa thì không
                # thấy). Nghỉ lâu hơn ca câu-lỗi rồi thử lại — vẫn rẻ hơn 70 giây phạt.
                raise GeminiWebFlaky("trả lời rỗng (có thể đang bị hãm tốc)", cho=8.0)
            if _la_loi_soan_san(raw):
                raise GeminiWebFlaky("web trả câu lỗi soạn sẵn: %s" % raw[:80])
            return raw
        except (GeminiWebStopped, GeminiWebMissing):
            raise
        except GeminiWebTimeout as e:
            loi_cuoi = e
            break
        except GeminiWebFlaky as e:
            # Phiên vẫn tốt (lượt trước/sau của chính nó vẫn chạy), nên KHÔNG dựng lại
            # phiên — dựng lại tốn thêm ~3 giây mỗi lần mà chẳng chữa được gì.
            loi_cuoi = e
            if lan >= retries:
                break
            cho = min(45.0, getattr(e, "cho", 2.0) * lan)
            if on_log:
                on_log("    [gemini-web] %s → nghỉ %.0fs rồi gọi lại (%d/%d)"
                       % (e, cho, lan, retries))
            for _ in range(int(cho * 2)):            # ngủ nhưng vẫn nghe nút Dừng
                if stop_event is not None and stop_event.is_set():
                    raise GeminiWebStopped()
                time.sleep(0.5)
            continue
        except GeminiWebQuota:
            raise                                   # để pool xoay tài khoản ngay
        except GeminiWebBlocked:
            raise                                   # nện tiếp chỉ tổ bị chặn lâu hơn
        except GeminiWebAuth as e:
            # Cookie có thể vừa được tiện ích đẩy bản mới: thử dựng lại phiên MỘT lần.
            loi_cuoi = e
            if lam_moi:
                _loai_phien(account_id, expected=p)
                raise
            lam_moi = True
            if on_log:
                on_log("    [gemini-web] cookie hỏng — dựng lại phiên bằng cookie mới nhất…")
            continue
        except Exception as e:                       # noqa: BLE001
            loi_cuoi = e if isinstance(e, GeminiWebError) else _dich_loi(e)
            if isinstance(loi_cuoi, (GeminiWebQuota, GeminiWebBlocked)):
                raise loi_cuoi
            if isinstance(loi_cuoi, GeminiWebAuth) and not lam_moi:
                lam_moi = True
                continue
            if lan < retries:
                cho = min(20, 3 * lan)
                if on_log:
                    on_log("    [gemini-web] %s → nghỉ %ds rồi thử lại (%d/%d)"
                           % (loi_cuoi, cho, lan, retries))
                for _ in range(int(cho * 2)):
                    if stop_event is not None and stop_event.is_set():
                        raise GeminiWebStopped()
                    time.sleep(0.5)
                # Lỗi mạng/stream đứt thường do phiên hỏng -> lượt sau dựng lại phiên.
                lam_moi = True
    # Timeout/stream đứt/auth cuối cùng chứng minh transport này không còn đáng tái
    # sử dụng. Rút và đóng ngay; request kế tiếp sẽ dựng phiên sạch từ cookie mới nhất.
    # Không drop với Flaky (trả rỗng/câu lỗi soạn sẵn): đó là lỗi nội dung, socket vẫn tốt.
    if (p is not None and loi_cuoi is not None and not isinstance(
            loi_cuoi, (GeminiWebFlaky, GeminiWebQuota, GeminiWebBlocked))):
        _loai_phien(account_id, expected=p,
                    background=isinstance(loi_cuoi, GeminiWebTimeout))
    raise loi_cuoi or GeminiWebError("không gọi được Gemini web")


def list_accounts():
    """Tài khoản cookie đang có (không kèm giá trị cookie)."""
    return store.list_accounts()


def _check_error_kind(error):
    if isinstance(error, GeminiWebAuth):
        return "auth"
    if isinstance(error, GeminiWebQuota):
        return "quota"
    if isinstance(error, GeminiWebBlocked):
        return "blocked"
    if isinstance(error, GeminiWebMissing):
        return "missing"
    return "error"


def _check_error_result(error, models=None):
    if not isinstance(error, GeminiWebError):
        error = _dich_loi(error)
    return {
        "ok": False,
        "kind": _check_error_kind(error),
        "msg": str(error),
        "models": list(models or []),
    }


def check(account_id, timeout=120, stop_event=None):
    """Làm nóng một phiên rồi hỏi một câu ngắn; không đóng phiên đang dịch."""
    if stop_event is not None and stop_event.is_set():
        raise GeminiWebStopped()
    ok, vi_sao = available()
    if not ok:
        return {"ok": False, "kind": "missing", "msg": vi_sao, "models": []}
    t0 = time.time()
    # Phiên ĐANG có trước lượt kiểm tra. Đối chiếu sau khi gọi _phien để biết nó có
    # âm thầm dựng lại hay không: _phien tự dựng lại khi cookie đổi HOẶC khi phiên đã
    # chết quá THU_LAI_PHIEN_CHET giây, nên phần lớn ca "tự chữa" xảy ra NGAY Ở ĐÂY,
    # trước cả câu thử — không so thì báo cáo sẽ nói nhầm là chưa phải chữa gì.
    with _PHIEN_LOCK:
        _truoc = _PHIEN.get(account_id)
    try:
        # Cookie đổi thì _phien tự dựng lại theo vân tay mới. Cookie không đổi thì dùng
        # phiên đang có để nút kiểm tra không đóng client giữa một lượt dịch.
        p = _phien(account_id, timeout=timeout, lam_moi=False)
    except Exception as e:                              # noqa: BLE001
        return _check_error_result(e)
    def _cau_thu():
        # model="gemini-flash-lite": câu thử chỉ để biết cookie còn gọi được. Đo
        # 04/09/2026 trên tài khoản free: Flash-Lite tốn 0 credit, Flash 2-6, Pro ~100
        # (hạn mức free là 600 credit/5 giờ) — không đáng đốt hạn mức của lượt dịch chỉ
        # để chào hỏi. Không khớp thì _chon_model tự rơi về model có thật của tài khoản.
        return ask(
            account_id, "Trả lời đúng một từ: OK", model="gemini-flash-lite",
            timeout=timeout, retries=1, stop_event=stop_event)

    # NÚT KIỂM TRA PHẢI TỰ CHỮA, RỒI MỚI BÁO (08/09/2026, người dùng yêu cầu).
    # Vì sao: lỗi auth ở đây gần như luôn là PHIÊN chết chứ không phải cookie chết —
    # __Secure-1PSID không đổi khi Google xoay __Secure-1PSIDTS (xem
    # _phien_chet_can_dung_lai). Dựng lại phiên là lấy được token mới từ cache xoay
    # cookie của thư viện / cookie trình duyệt, tức đúng việc người dùng vẫn làm tay
    # bằng nút 'Gửi vào app'. Chỉ khi dựng lại VẪN hỏng mới thật sự cần bấm tay — và
    # lúc đó phải nói thẳng tên tài khoản, thay vì để người dùng bấm lại cả kho.
    def _con_khach(phien):
        """Phiên đang là KHÁCH (chưa đăng nhập) chứ không phải của tài khoản.

        ĐÂY LÀ THỦ PHẠM của "check báo sống mà dịch báo hết hạn" (đo 09/09/2026 trên
        6 tài khoản acc-*0076): phiên UNAUTHENTICATED VẪN TRẢ LỜI ĐƯỢC câu thử, vì
        Gemini phục vụ khách vô danh bình thường. Nên "trả lời: OK" một mình KHÔNG
        chứng minh cookie còn sống — phải soi cả trạng thái phiên, đúng như
        list_model_info đã làm ("danh sách lúc này là của KHÁCH").
        """
        return str(getattr(phien, "trang_thai", "") or "") == "UNAUTHENTICATED"

    da_dung_lai = _truoc is not None and p is not _truoc
    try:
        if _con_khach(p):
            raise GeminiWebAuth("phiên CHƯA ĐĂNG NHẬP (UNAUTHENTICATED) — câu thử vẫn "
                                "trả lời được vì Gemini phục vụ cả khách vô danh")
        raw = _cau_thu()
    except GeminiWebStopped:
        raise
    except Exception as e:                              # noqa: BLE001
        loi = e if isinstance(e, GeminiWebError) else _dich_loi(e)
        if _check_error_kind(loi) != "auth":
            return _check_error_result(e, p.models)
        try:
            p = _phien(account_id, timeout=timeout, lam_moi=True)
            if _con_khach(p):
                raise GeminiWebAuth("dựng lại phiên rồi vẫn CHƯA ĐĂNG NHẬP")
            raw = _cau_thu()
            da_dung_lai = True
        except GeminiWebStopped:
            raise
        except Exception as e2:                         # noqa: BLE001
            kq = _check_error_result(e2, p.models)
            kq["can_bam_tay"] = True
            kq["msg"] = ("CẦN BẤM 'Gửi vào app' cho tài khoản này — đã thử dựng lại "
                         "phiên mà vẫn hỏng (%s)" % str(kq.get("msg") or "")[:110])
            return kq
    elapsed = time.time() - t0
    return {
        "ok": True,
        "kind": "ok",
        "can_bam_tay": False,
        "da_dung_lai": da_dung_lai,
        "msg": "%strả lời: %s (%.1fs)" % (
            "phiên đã chết, ĐÃ TỰ DỰNG LẠI — " if da_dung_lai else "",
            raw[:40], elapsed),
        "models": p.models,
        # Kèm bản đầy đủ để ô chọn model trong giao diện đổ thẳng từ kết quả kiểm tra,
        # khỏi bắt người dùng bấm thêm một nút nữa. Bên gọi cũ chỉ đọc 'models' nên
        # thêm khoá này không đụng gì tới chúng.
        "model_info": _model_info_cua(p),
        "trang_thai": str(getattr(p, "trang_thai", "") or ""),
        "elapsed": elapsed,
    }


def check_all(account_ids=None, timeout=120, max_workers=6, on_result=None,
              stop_event=None):
    """Kiểm tra/làm nóng toàn bộ kho, song song theo tài khoản và đánh dấu cookie trùng.

    Bản ghi trùng __Secure-1PSID không được gọi lần hai: đó là cùng một phiên, vừa tốn
    lượt vừa không tạo thêm làn hay hạn mức. Kết quả vẫn có đủ một dòng cho mỗi bản ghi.
    """
    source_ids = store.account_ids() if account_ids is None else account_ids
    ids = list(dict.fromkeys(source_ids))
    if stop_event is not None and stop_event.is_set():
        raise GeminiWebStopped()
    duplicate_of = {}
    for group in store.duplicate_account_groups(ids):
        leader = group[0]
        for acc_id in group[1:]:
            duplicate_of[acc_id] = leader
    leaders = [acc_id for acc_id in ids if acc_id not in duplicate_of]
    results = {}
    done = 0

    def emit(acc_id, result):
        nonlocal done
        done += 1
        result = dict(result or {})
        result["id"] = acc_id
        results[acc_id] = result
        if on_result is not None:
            try:
                on_result(acc_id, dict(result), done, len(ids))
            except Exception:
                pass

    workers = max(1, min(int(max_workers or 1), len(leaders) or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(check, acc_id, timeout, stop_event): acc_id
            for acc_id in leaders
        }
        for future in concurrent.futures.as_completed(futures):
            acc_id = futures[future]
            try:
                result = future.result()
            except GeminiWebStopped:
                raise
            except Exception as e:                      # noqa: BLE001
                result = _check_error_result(e)
            emit(acc_id, result)

    for acc_id in ids:
        leader = duplicate_of.get(acc_id)
        if not leader:
            continue
        base = results.get(leader) or {}
        emit(acc_id, {
            "ok": bool(base.get("ok")),
            "kind": "duplicate",
            "duplicate_of": leader,
            "msg": "trùng cookie phiên với '%s' — không tạo thêm làn/hạn mức" % leader,
            "models": list(base.get("models") or []),
            "model_info": list(base.get("model_info") or []),
        })

    rows = [results[acc_id] for acc_id in ids]
    return {
        "total": len(rows),
        "live": sum(1 for row in rows if row.get("kind") == "ok"),
        "failed": sum(1 for row in rows
                      if row.get("kind") not in ("ok", "duplicate")),
        "duplicates": sum(1 for row in rows if row.get("kind") == "duplicate"),
        # Tài khoản mà dựng lại phiên VẪN không cứu được -> chỉ những cái này mới cần
        # người dùng mở tiện ích Chrome bấm 'Gửi vào app'. Khoá THÊM, bên gọi cũ không đọc.
        "can_bam_tay": [row["id"] for row in rows if row.get("can_bam_tay")],
        "results": rows,
    }


def _kiem_lai_tung_cai(report, timeout, stop_event):
    """Tài khoản trượt lúc kiểm SONG SONG -> hỏi lại MỘT MÌNH nó một lần rồi mới loại.

    Đo 27/09/2026 (Gemini web, 7 tài khoản vừa bấm 'Gửi vào app'): kiểm 6 cái cùng lúc
    báo 2/7 sống lúc 23:12, 5/7 lúc 23:25; check() LẦN LƯỢT từng cái -> 7/7. Phần lớn
    "hỏng" là lỗi TẠM khi dồn cùng lúc, cookie vẫn tốt — loại chúng là bỏ oan làn chạy.
    Chỉ kiểm lại cái trượt, nên kho khoẻ thì không tốn thêm gì; cái hỏng thật (auth) tốn
    thêm đúng một câu thử. Sửa tại chỗ report (results/live/failed/can_bam_tay) và ghi
    'hoi_lai' = các tài khoản vừa được cứu."""
    rows = list(report.get("results") or [])
    hoi_lai = []
    for i, row in enumerate(rows):
        if row.get("kind") in ("ok", "duplicate", "missing") or not row.get("id"):
            continue
        if stop_event is not None and stop_event.is_set():
            raise GeminiWebStopped()
        try:
            kq = check(row["id"], timeout=min(float(timeout or 90), 90.0),
                       stop_event=stop_event)
        except GeminiWebStopped:
            raise
        except Exception as e:                           # noqa: BLE001
            kq = _check_error_result(e)
        kq = dict(kq or {}, id=row["id"], lan_dau=row.get("kind"))
        if kq.get("ok"):
            hoi_lai.append(row["id"])
        rows[i] = kq
    if hoi_lai:
        song = {r["id"] for r in rows if r.get("kind") == "ok"}
        for i, row in enumerate(rows):
            if row.get("kind") == "duplicate" and row.get("duplicate_of") in song:
                rows[i] = dict(row, ok=True)
    report["results"] = rows
    report["live"] = sum(1 for r in rows if r.get("kind") == "ok")
    report["failed"] = sum(1 for r in rows if r.get("kind") not in ("ok", "duplicate"))
    report["can_bam_tay"] = [r["id"] for r in rows if r.get("can_bam_tay")]
    report["hoi_lai"] = hoi_lai
    return report


def _preflight_signature(ids):
    """Chữ ký cache không chứa giá trị cookie; cookie đổi thì mốc updated đổi."""
    accounts = (store.load_store().get("accounts") or {})
    return tuple(
        (acc_id, (accounts.get(acc_id) or {}).get("updated") or 0)
        for acc_id in ids)


def preflight_accounts(account_ids=None, timeout=120, max_workers=6,
                       on_result=None, stop_event=None, force=False,
                       max_age=PREFLIGHT_CACHE_SECONDS):
    """Tiền kiểm tự động và trả đúng các tài khoản sống, độc lập để đưa vào pool.

    Cùng một chữ ký kho chỉ có một lượt kiểm tra chạy tại một thời điểm. Lượt gọi khác
    chờ kết quả đó thay vì cùng gửi câu thử và giẫm lên phiên.
    """
    source_ids = store.account_ids() if account_ids is None else account_ids
    ids = list(dict.fromkeys(source_ids))
    signature = _preflight_signature(ids)

    while True:
        now = time.time()
        with _PREFLIGHT_LOCK:
            cached = _PREFLIGHT_CACHE.get(signature)
            fresh = (cached is not None and not force
                     and (max_age is None
                          or now - cached.get("checked_at", 0) <= max(0, max_age)))
            if fresh:
                report = copy.deepcopy(cached)
                report["cached"] = True
                return report
            waiter = _PREFLIGHT_INFLIGHT.get(signature)
            if waiter is None:
                waiter = threading.Event()
                _PREFLIGHT_INFLIGHT[signature] = waiter
                break
        # Một nút/luồng khác đang kiểm đúng kho này. Kết quả của nó là kết quả mới nhất,
        # kể cả người gọi ban đầu yêu cầu force.
        waiter.wait()
        force = False

    try:
        report = check_all(
            ids, timeout=timeout, max_workers=max_workers, on_result=on_result,
            stop_event=stop_event)
        report = dict(report)
        report = _kiem_lai_tung_cai(report, timeout, stop_event)
        report["usable_accounts"] = [
            row["id"] for row in report.get("results") or []
            if row.get("kind") == "ok"
        ]
        report["signature"] = signature
        report["checked_at"] = time.time()
        report["cached"] = False
        with _PREFLIGHT_LOCK:
            _PREFLIGHT_CACHE.clear()
            _PREFLIGHT_CACHE[signature] = copy.deepcopy(report)
        return report
    finally:
        with _PREFLIGHT_LOCK:
            event = _PREFLIGHT_INFLIGHT.pop(signature, None)
            if event is not None:
                event.set()


def close_all():
    with _PHIEN_LOCK:
        ps = list(_PHIEN.values())
        _PHIEN.clear()
        _PHIEN_BUILD_LOCKS.clear()
    for p in ps:
        _dong_phien(p, timeout=10)


def _cli(argv=None):
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Thử Gemini web bằng cookie đã lưu.")
    ap.add_argument("--account", default=None, help="id tài khoản (mặc định: mới nhất)")
    ap.add_argument("--check", action="store_true", help="Kiểm tra phiên + liệt kê model")
    ap.add_argument("--models", action="store_true",
                    help="Chỉ liệt kê model của tài khoản (KHÔNG tốn lượt hỏi)")
    ap.add_argument("--ask", default=None, help="Gửi một câu hỏi")
    ap.add_argument("--model", default=None, help="Tên model kiểu API (gemini-…-flash-lite)")
    ap.add_argument("--timeout", type=float, default=180)
    a = ap.parse_args(argv)

    ok, vi_sao = available()
    if not ok:
        print(vi_sao)
        return 2
    acc = a.account or (store.account_ids()[0] if store.account_ids() else None)
    if not acc:
        print("Kho cookie rỗng — cài tiện ích gemini_cookie_ext/ rồi bấm 'Gửi vào app'.")
        return 2
    print("Tài khoản: %s" % acc)
    if a.models:
        kq = list_model_info(acc, timeout=a.timeout)
        print("%s  (trạng thái: %s)" % (kq.get("msg"), kq.get("trang_thai") or "?"))
        for m in kq.get("models") or []:
            print(" %-18s %-40s %s" % (m.get("id"), m.get("nhan"),
                                       "" if m.get("available") else "(không chọn được)"))
        return 0 if kq.get("ok") else 1
    if a.check or not a.ask:
        kq = check(acc, timeout=a.timeout)
        print(json.dumps(kq, ensure_ascii=False, indent=1))
        return 0 if kq["ok"] else 1
    print(ask(acc, a.ask, model=a.model, timeout=a.timeout,
              on_log=lambda s: print(s, flush=True)))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
