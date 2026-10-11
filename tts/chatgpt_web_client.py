# -*- coding: utf-8 -*-
"""Gọi ChatGPT WEB (chatgpt.com) bằng COOKIE thay cho khoá API.

Song sinh với ``gemini_web_client.py``: cùng vai trò, cùng chữ ký hàm, cùng cách báo
lỗi, để ``srt_translate_core.py`` chỉ phải CHỌN hàm chứ không phải biết provider nào ra
sao. Khác nhau ở đúng một chỗ: phần nói chuyện với máy chủ.

    gemini_cookie_ext/ (tiện ích Chrome)  ->  chatgpt_cookie_store.py (kho cookie)
                                          ->  FILE NÀY  ->  srt_translate_core.py

VÌ SAO TỰ VIẾT GIAO THỨC Ở ĐÂY, khác hẳn đường Gemini (đi nhờ thư viện gemini_webapi):
không có thư viện bên thứ ba nào cho ChatGPT web đủ sống để tin. Nên phần giao thức
nằm ngay đây, viết gọn và có chú thích, để lúc OpenAI đổi thì sửa được tại chỗ.

BỐN BƯỚC của một lượt hỏi (mỗi bước hỏng ra một loại lỗi RIÊNG, đọc log là biết ngay):

  1. GET  /api/auth/session                  -> accessToken (Bearer) của phiên đăng nhập
  2. GET  /                                  -> lấy 'dpl' + đường dẫn file .js (làm mồi
                                                cho bước 3; hỏng thì vẫn chạy tiếp)
  3. POST /backend-api/sentinel/chat-requirements
                                             -> token phiên chat + đề bài proof-of-work
  4. POST /backend-api/conversation          -> stream SSE, gom lại thành CHỮ

HAI THỨ QUYẾT ĐỊNH SỐNG CHẾT, ghi ra đây để khỏi đoán mò khi gỡ lỗi:

  * ``cf_clearance`` gắn với (IP + User-Agent). App chạy ngay trên máy có Chrome nên IP
    khớp sẵn; User-Agent thì PHẢI dùng đúng chuỗi tiện ích đã đẩy sang (lưu trong kho),
    sai một ký tự là Cloudflare chặn. Vì thế mọi request đi qua ``curl_cffi`` với
    ``impersonate`` để dấu vân tay TLS cũng giống Chrome, không phải vân tay Python.
  * ``proof-of-work`` (header ``openai-sentinel-proof-token``): OpenAI ra một 'seed' +
    'difficulty', client phải tìm chuỗi băm SHA3-512 nhỏ hơn ngưỡng. Thuật toán nằm ở
    ``_proof_token`` bên dưới. Nếu OpenAI bật thêm ``turnstile`` thì đường này KHÔNG
    qua được — lúc đó ném ChatGPTWebBlocked kèm câu nói rõ, đừng thử lại cho tốn.

HẠN CHẾ ĐÃ BIẾT, ghi rõ để khỏi kỳ vọng nhầm:
  * KHÔNG có tham số nhiệt độ (temperature) — web không cho chỉnh; tham số nhận vào chỉ
    để trùng chữ ký với các provider khác.
  * Mỗi tài khoản chạy TUẦN TỰ (semaphore 1 làn), đúng như ngồi gõ tay trên trình duyệt.
    Muốn nhanh hơn thì THÊM TÀI KHOẢN, đừng nới số lượt song song.
  * Đây là cửa dành cho người dùng cuối, không phải API chính thức. OpenAI có thể đổi
    giao thức bất cứ lúc nào, và dùng quá đà thì tài khoản có thể bị hạn chế.

HÂM NÓNG PHIÊN (thêm 28/08/2026) — vì sao đường này cần mà đường Gemini thì không:

  * ``gemini_web_client`` dựng client với ``auto_refresh=True, refresh_interval=600``:
    thư viện TỰ đi xin ``__Secure-1PSIDTS`` mới, nên sau MỘT lần đẩy cookie tốt là app
    tự nuôi được phiên. Cookie ``google.com`` còn được hâm miễn phí bởi mọi tab Google
    khác đang mở (tiện ích nghe cả SID/SAPISID/NID).
  * ``chatgpt.com`` thì không ai hâm hộ: cookie của nó CHỈ đổi khi chính trang đó được
    nạp. Bản đầu dựng phiên từ ẢNH CHỤP kho rồi vứt hết cookie máy chủ trả về, nên phần
    mục theo giờ (``__cf_bm`` ~30 phút, token phiên NextAuth) hết hạn lúc nào là hỏng
    lúc đó -> người dùng phải mở tab Chrome rồi bấm 'Gửi vào app' lần nữa.

  Nay làm đúng hai việc một tab đang mở vẫn làm:
    1. GHI NGƯỢC (``_ghi_cookie_ve_kho``) — mọi cookie máy chủ Set-Cookie trong một lượt
       gọi được gộp về kho, kể cả khi lượt đó HỎNG: vé Cloudflare vừa cấp vẫn tốt.
    2. NGÁP ĐỀU (``bat_ham_nong``) — mỗi ``HAM_NONG_PHUT`` phút gọi lại bước 1 cho từng
       tài khoản để Cloudflare cấp ``__cf_bm`` mới và NextAuth xoay token phiên.

  Hâm nóng KHÔNG cứu được cookie đã chết hẳn — chết rồi thì vẫn phải đăng nhập lại và
  đẩy sang. Nó chỉ giữ cho cookie đang sống khỏi chết vì bỏ quên.

Chạy thử một tài khoản (không cần mở GUI):

    python chatgpt_web_client.py --list
    python chatgpt_web_client.py --check <account_id>
    python chatgpt_web_client.py --ask <account_id> "Dịch sang tiếng Việt: 你好"
"""

import base64
import concurrent.futures
import copy
import hashlib
import json
import os
import random
import re
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import chatgpt_cookie_store as store

# --------------------------------------------------------------------------- #
#  Nạp thư viện (mềm): thiếu thì báo bằng lỗi có hướng dẫn, không làm chết app.
# --------------------------------------------------------------------------- #
try:
    from curl_cffi import requests as _cffi
    _IMPORT_ERR = None
except Exception as e:                                   # noqa: BLE001
    _cffi = None
    _IMPORT_ERR = e

CAI_DAT = "pip install curl_cffi"

BASE = "https://chatgpt.com"

# Dấu vân tay TLS/HTTP2 giả lập. Phải là một hồ sơ Chrome đời gần với Chrome thật của
# người dùng, vì cf_clearance gắn với User-Agent.
IMPERSONATE = os.environ.get("CHATGPT_WEB_IMPERSONATE") or "chrome"

# User-Agent dự phòng khi kho chưa lưu được UA thật của trình duyệt.
UA_DU_PHONG = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# Số lượt gọi chạy cùng lúc trên MỖI tài khoản. MẶC ĐỊNH 1 = gửi lô sau chỉ khi lô
# trước đã xong, đúng như ngồi gõ tay trên trình duyệt (xem lý do ở gemini_web_client).
CONCURRENCY = int(os.environ.get("CHATGPT_WEB_CONCURRENCY") or 1)

# Chờ tối đa cho một lượt gọi (giây) nếu bên gọi không nói gì.
TIMEOUT_MAC_DINH = 300

# Hàng đợi phiên chỉ là lớp an toàn thứ hai; pool phía trên vốn đã bảo đảm một request
# trên mỗi tài khoản.
SESSION_QUEUE_TIMEOUT = max(
    30, int(os.environ.get("CHATGPT_WEB_SESSION_QUEUE_TIMEOUT") or 180))

# accessToken của /api/auth/session sống khá lâu nhưng không nói rõ hạn; xin lại theo
# chu kỳ ngắn vẫn rẻ hơn nhiều so với hỏng một lô dịch dài.
TOKEN_SONG_GIAY = int(os.environ.get("CHATGPT_WEB_TOKEN_TTL") or 25 * 60)

# Dọn (ẩn) đoạn chat vừa tạo sau mỗi lô. MẶC ĐỊNH TẮT — và cố ý tắt:
#
# Thân request đã bật ``history_and_training_disabled`` nên bình thường chẳng có gì để
# dọn. Nếu OpenAI bỏ qua cờ đó thì dịch một phim sẽ đẻ ra vài trăm đoạn chat rác, lúc ấy
# bật cờ này lên là app tự ẩn chúng đi. Nhưng ẩn chat là ĐỘNG VÀO TÀI KHOẢN người dùng,
# mà app thì đoán id hội thoại từ chính stream nó vừa tạo — bật sẵn theo mặc định là tự
# tiện sửa dữ liệu bên ngoài mà không ai yêu cầu. Ai muốn thì đặt:
#
#     CHATGPT_WEB_CLEAN_CHATS=1
XOA_HOI_THOAI = (os.environ.get("CHATGPT_WEB_CLEAN_CHATS") or "").strip() in ("1", "true", "yes")

# Model mặc định. Web đặt tên model khác API, và mỗi tài khoản (free/plus) có danh sách
# riêng -> 'auto' để OpenAI tự chọn model tài khoản đó đang được dùng.
MODEL_MAC_DINH = "auto"
# Xin model MẠNH NHẤT tài khoản đang có (02/10/2026, bước tiêu đề). 'auto' để OpenAI tự
# quyết: đo cùng ngày nó có trả lời bằng gpt-5-6, nhưng hết lượt model lớn thì router âm
# thầm hạ xuống bản mini mà app không hay. Không ghi cứng tên model — chọn bản số cao nhất
# không phải mini/nano trong danh sách THẬT của tài khoản, OpenAI ra bản mới là tự lấy.
MODEL_TOT_NHAT = "tot-nhat"
# 06/10/2026 (người dùng: "dùng model tốt nhất cho đến kém nhất"): 'tot-nhat' nay là một
# CHUỖI hạ dần chứ không còn "mạnh nhất, hết lượt thì nhảy thẳng về auto". Đo cùng ngày
# trên acc0 gói Free: gpt-5-6 "hit your limit", gpt-5-5 VẪN trả lời, còn 'auto' trả lời
# bằng gpt-5-6-mini — tức bản cũ bỏ qua cả một bậc model còn dùng được. Lô dịch 150 câu
# bằng gpt-5-5 mất 19,6s (auto 23,9s), dư xa trần 60s.
# Model hết lượt của TÀI KHOẢN nào thì nghỉ riêng tài khoản đó, các lô sau khỏi thử lại
# (mỗi lần thử một model đã cạn = một request vô ích). Không có con số công bố nên lấy
# 3 giờ; đặt CHATGPT_WEB_HET_LUOT_GIAY để đổi.
try:
    HET_LUOT_NGHI_GIAY = max(60.0, float(os.environ.get("CHATGPT_WEB_HET_LUOT_GIAY")
                                         or 3 * 3600))
except (TypeError, ValueError):
    HET_LUOT_NGHI_GIAY = 3 * 3600.0
# Model trả lỗi máy chủ 5xx (đo: gpt-5-3-mini ăn 500 hai lần liền) thì nghỉ ngắn hơn —
# có thể chỉ là chập chờn một lúc.
MODEL_LOI_NGHI_GIAY = 10 * 60.0
_MODEL_NGHI = {}                       # (tài khoản, model) -> mốc hết nghỉ (time.time)
_MODEL_NGHI_LOCK = threading.Lock()
# Chỉ xếp các model chat CHUẨN: gpt-<số>[-<số>…][-mini|-nano]. Bỏ 'research' (nghiên cứu
# sâu, đo: lỗi 500), các bản '-t-mini' (tên lạ; đo: '-t-mini-mini' trả lời bằng chính
# gpt-5-6-mini) và 'auto' (luôn đứng CUỐI chuỗi làm lưới đỡ).
_MAU_MODEL_CHUAN = re.compile(r"^gpt-\d+(?:-\d+)*(?:-(mini|nano))?$", re.I)


def _so_phut_ham():
    """Đọc chu kỳ hâm nóng từ môi trường; gõ sai thì về mặc định, KHÔNG làm chết app."""
    try:
        return max(0.0, float(os.environ.get("CHATGPT_WEB_WARM_MINUTES") or 10))
    except (TypeError, ValueError):
        return 10.0


# Số lượt gọi bước 1 TRONG CÙNG MỘT PHIÊN trước khi chịu thua vì 403. Xem _lay_token:
# có lúc phiên mới tinh ăn 1-2 lượt 403 "chào hỏi" rồi mới qua (đo 3/3 lần), có lúc
# không — nên phải thử lại chứ không được kết luận ngay ở lượt đầu.
LAP_LAI_403 = max(1, int(os.environ.get("CHATGPT_WEB_403_RETRY") or 3))
CHO_LAI_403_GIAY = 0.5

# Chu kỳ "ngáp" giữ phiên còn sống, tính bằng PHÚT. Đặt 0 để tắt hẳn.
# 10 phút chọn theo mốc ngắn nhất đã biết: __cf_bm của Cloudflare sống ~30 phút, nên
# ngáp 3 lần trong một vòng đời của nó thì lỡ một lượt vẫn chưa chết.
HAM_NONG_PHUT = _so_phut_ham()


class ChatGPTWebError(RuntimeError):
    """Lỗi tạm — cứ thử lại/đổi tài khoản."""


class ChatGPTWebTimeout(ChatGPTWebError):
    """Một lô vượt deadline: hủy request, bỏ phiên và chuyển nguyên lô sang cookie khác."""


class ChatGPTWebAuth(ChatGPTWebError):
    """Cookie hỏng/hết hạn — phải mở tiện ích lấy lại cookie."""


class ChatGPTWebQuota(ChatGPTWebError):
    """Tài khoản này cạn hạn mức — xoay sang tài khoản khác."""


class ChatGPTWebBlocked(ChatGPTWebError):
    """Cloudflare/OpenAI chặn (IP, tài khoản, hoặc đòi turnstile) — dừng, đừng nện tiếp."""


class ChatGPTWebMissing(ChatGPTWebError):
    """Chưa cài thư viện curl_cffi."""


class ChatGPTWebFlaky(ChatGPTWebError):
    """Máy chủ trả 200 nhưng nội dung không dùng được (rỗng, hoặc câu lỗi soạn sẵn).

    Gọi lại là được, nên KHÔNG để nó chui lên bộ điều phối: ở trên đó mọi 'lỗi tạm' đều
    bị phạt cho key nghỉ ~70 giây — luật đúng cho 429 theo phút của API, nhưng với đường
    cookie chỉ có 1-2 tài khoản thì 70 giây đó là 70 giây ngồi không.

    cho: số giây chờ CƠ SỞ trước khi gọi lại (nhân theo số lần thử)."""

    def __init__(self, msg="", cho=2.0):
        super().__init__(msg)
        self.cho = cho


class ChatGPTWebStopped(Exception):
    """Người dùng bấm Dừng."""


def _la_het_luot_model(e):
    """Câu web báo khi tài khoản cạn lượt của model ĐÃ XIN (không phải cạn cả tài khoản)."""
    return bool(re.search(r"hit your limit", str(e or ""), re.I))


# Câu lỗi soạn sẵn của giao diện ChatGPT: HTTP vẫn 200, chữ vẫn về, nhưng nội dung là
# thông báo hỏng chứ không phải bản dịch. CHỈ thêm mẫu ĐÃ THẤY THẬT vào danh sách này —
# nhét cả câu từ chối ("I can't help with that") vào đây là sai: từ chối thì gọi lại vẫn
# từ chối, chỉ tổ đốt thêm lượt.
_LOI_SOAN_SAN = (
    r"something went wrong",
    r"there was an error generating a response",
    r"đã có lỗi xảy ra",
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
    if _cffi is None:
        return False, ("Chưa cài thư viện curl_cffi (%s). Chạy: %s"
                       % (type(_IMPORT_ERR).__name__, CAI_DAT))
    return True, ""


# --------------------------------------------------------------------------- #
#  PROOF-OF-WORK (header openai-sentinel-proof-token)
#
#  OpenAI đưa 'seed' + 'difficulty'; client phải tìm một chuỗi cấu hình sao cho
#  sha3_512(seed + base64(json(cấu_hình))) có phần đầu <= difficulty. Cấu hình mô phỏng
#  vài thuộc tính trình duyệt (kích thước màn hình, giờ, User-Agent, ngôn ngữ…).
#
#  Không đoán được ĐÚNG khuôn cấu hình OpenAI đang chờ — họ đổi luôn. Nhưng phép kiểm
#  ở phía máy chủ chỉ băm lại đúng chuỗi ta gửi, nên nội dung cấu hình không cần khớp
#  từng ô; cái phải đúng là ĐỘ KHÓ và khuôn base64. Vì thế bước này hỏng thì hỏng ở
#  bước 4 với 403, không phải hỏng âm thầm.
# --------------------------------------------------------------------------- #
_MAN_HINH = (3000, 4000, 6000)
_LOI = (8, 12, 16, 24)
_KHOA_NAVIGATOR = ("hardwareConcurrency", "language", "languages", "webdriver",
                   "deviceMemory", "userAgent", "platform", "vendor")
_KHOA_DOCUMENT = ("location", "referrer", "cookie", "hidden", "title")
_KHOA_WINDOW = ("innerWidth", "innerHeight", "screenX", "screenY", "devicePixelRatio")

_BAT_DAU = time.time() * 1000


def _cau_hinh_pow(ua, dpl="", script=""):
    """Mảng cấu hình đem đi băm. Các ô ngẫu nhiên cố ý đổi mỗi phiên, giống trình duyệt
    thật mỗi máy một khác."""
    gio = datetime.now(timezone(timedelta(hours=-5)))
    return [
        random.choice(_MAN_HINH) + random.choice(_LOI),
        gio.strftime("%a %b %d %Y %H:%M:%S") + " GMT-0500 (Eastern Standard Time)",
        4294705152,
        0,
        ua,
        script,
        dpl,
        "en-US",
        "en-US,en",
        0,
        random.choice(_KHOA_NAVIGATOR),
        random.choice(_KHOA_DOCUMENT),
        random.choice(_KHOA_WINDOW),
        int(time.time() * 1000 - _BAT_DAU),
        str(uuid.uuid4()),
        "",
        random.choice(_LOI),
        int(time.time() * 1000),
    ]


def _proof_token(seed, difficulty, ua, dpl="", script="", vong=200000):
    """Tìm lời giải. Không ra thì trả token dự phòng (máy chủ vẫn nhận trong nhiều ca)."""
    cfg = _cau_hinh_pow(ua, dpl, script)
    do_dai = len(difficulty or "")
    if not do_dai:
        difficulty, do_dai = "0", 1
    for i in range(vong):
        cfg[3] = i
        cfg[9] = int(time.time() * 1000 - _BAT_DAU)
        chuoi = base64.b64encode(
            json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).encode()).decode()
        bam = hashlib.sha3_512(((seed or "") + chuoi).encode()).hexdigest()
        if bam[:do_dai] <= difficulty:
            return "gAAAAAB" + chuoi
    du_phong = base64.b64encode(('"%s"' % (seed or "")).encode()).decode()
    return "gAAAAABwQ8Lk5FbGpA2NcR9dShT6gYjU7VxZ4D" + du_phong


def _requirements_token(ua, dpl="", script=""):
    """Token gửi kèm ở BƯỚC 3 (chưa có seed): chỉ cần hai chữ số 0 đầu chuỗi băm."""
    cfg = _cau_hinh_pow(ua, dpl, script)
    for i in range(500000):
        cfg[3] = i
        chuoi = base64.b64encode(
            json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).encode()).decode()
        if hashlib.sha3_512(chuoi.encode()).hexdigest()[:2] == "00":
            return "gAAAAAC" + chuoi
    return "gAAAAAC" + chuoi


# --------------------------------------------------------------------------- #
#  Phiên theo TÀI KHOẢN
# --------------------------------------------------------------------------- #
class _Phien:
    __slots__ = ("session", "van_tay", "tao_luc", "sem", "models", "ua",
                 "device_id", "token", "token_luc", "dpl", "script", "model_vua_dung")

    def __init__(self, session, van_tay, sem, ua, device_id):
        self.session = session
        self.van_tay = van_tay
        self.tao_luc = time.time()
        self.sem = sem
        self.models = []
        self.ua = ua
        self.device_id = device_id
        self.token = None
        self.token_luc = 0.0
        self.dpl = ""
        self.script = ""
        self.model_vua_dung = None      # model THẬT trả lời lượt gần nhất (metadata stream)


_PHIEN = {}
_PHIEN_LOCK = threading.Lock()
_PHIEN_BUILD_LOCKS = {}

# Kết quả tiền kiểm dùng lại trong một khoảng ngắn nếu kho cookie không đổi.
PREFLIGHT_CACHE_SECONDS = 30 * 60
_PREFLIGHT_LOCK = threading.Lock()
_PREFLIGHT_CACHE = {}
_PREFLIGHT_INFLIGHT = {}


def _van_tay(cookies):
    """Dấu nhận biết bộ cookie — đổi nghĩa là người dùng đăng nhập lại/đổi tài khoản.

    Đi qua gia_tri_phien vì chatgpt.com CHIA MẢNH cookie phiên (`…session-token.0/.1`):
    tra thẳng tên trần thì mọi tài khoản đều có vân tay rỗng, và vân tay rỗng nghĩa là
    phiên không bao giờ được dựng lại khi người dùng đăng nhập tài khoản khác."""
    return (store.gia_tri_phien(cookies) or "")[-24:]


def _doc_cookie(acc_id):
    rec = store.get_account(acc_id)
    if not rec:
        co = ", ".join(a["id"] for a in store.list_accounts()) or "(kho rỗng)"
        raise ChatGPTWebAuth("Không có tài khoản cookie '%s'. Đang có: %s" % (acc_id, co))
    ck = rec.get("cookies") or {}
    if not store.da_dang_nhap(ck):
        raise ChatGPTWebAuth(
            "Tài khoản '%s' thiếu %s (kể cả dạng chia mảnh .0/.1) — hãy đăng nhập lại "
            "chatgpt.com rồi bấm 'Gửi vào app'." % (acc_id, store.COOKIE_BAT_BUOC))
    # CỐ Ý trả nguyên bộ cookie, KHÔNG ghép mảnh lại trước khi gửi: trình duyệt gửi đủ
    # các mảnh và chính máy chủ ghép theo số thứ tự. Tự ghép thành một cookie tên trần
    # là gửi một thứ trình duyệt không bao giờ gửi.
    ua = rec.get("ua") or UA_DU_PHONG
    sach = store.bo_cookie_rac(ck)
    if len(sach) < len(ck):
        # Kho cũ còn tích cookie theo từng cuộc trò chuyện -> dọn hẳn (không gọi mạng).
        store.thay_cookie(acc_id, sach, source="app dọn cookie hội thoại")
        ck = sach
    if store.phien_bi_tron(ck):
        ck = _chua_phien_tron(acc_id, ck, ua)
    return ck, ua


def _tach_kieu_phien(cookies, giu_manh):
    """Bộ cookie chỉ còn MỘT kiểu cookie phiên: các mảnh `.N` (giu_manh) hoặc tên trần."""
    ten = store.COOKIE_BAT_BUOC
    return {k: v for k, v in (cookies or {}).items()
            if not store.la_ho_phien(k) or ((k != ten) == bool(giu_manh))}


def _chua_phien_tron(acc_id, cookies, ua):
    """Kho đang giữ CẢ kiểu liền lẫn kiểu chia mảnh của cookie phiên -> chữa tại chỗ.

    Máy chủ nối mọi cookie trùng tên phiên thành một chuỗi rác nên bộ trộn luôn "không
    có accessToken". Đo 05/10/2026 trên 6 tài khoản thật: nguyên trạng hỏng 6/6, tách
    riêng từng kiểu sống 6/6 — tức cookie người dùng gửi KHÔNG hỏng, chỉ kho trộn hỏng.
    Thử kiểu chia mảnh trước (đúng thứ trình duyệt đang gửi), không được thì kiểu liền;
    kiểu nào lấy được token thì GHI LẠI vào kho. Không kiểu nào sống thì trả kiểu chia
    mảnh để bước 1 báo lỗi như thường."""
    for giu_manh in (True, False):
        thu = _tach_kieu_phien(cookies, giu_manh)
        if not store.da_dang_nhap(thu):
            continue
        try:
            s = _tao_session(thu, ua)
            try:
                r = None
                for _lan in range(max(1, LAP_LAI_403)):
                    r = s.get(BASE + "/api/auth/session",
                              headers={"accept": "application/json"}, timeout=40)
                    if r.status_code != 403:
                        break
                    time.sleep(CHO_LAI_403_GIAY)
                song = r is not None and r.status_code == 200 and bool(
                    (r.json() or {}).get("accessToken"))
            finally:
                try:
                    s.close()
                except Exception:                        # noqa: BLE001
                    pass
        except Exception:                                # noqa: BLE001 - mạng/thư viện
            song = False
        if song:
            store.thay_cookie(acc_id, thu)
            return thu
    return _tach_kieu_phien(cookies, True)


def _tao_session(cookies, ua):
    if _cffi is None:
        raise ChatGPTWebMissing("Chưa cài curl_cffi. Chạy: %s" % CAI_DAT)
    s = _cffi.Session(impersonate=IMPERSONATE)
    s.headers.update({
        "user-agent": ua,
        "accept-language": "en-US,en;q=0.9",
        "origin": BASE,
        "referer": BASE + "/",
    })
    for k, v in (cookies or {}).items():
        try:
            s.cookies.set(k, v, domain="chatgpt.com")
        except Exception:                                # noqa: BLE001 - cookie lẻ hỏng
            pass
    return s


def _cookie_cua_session(session):
    """Cookie chatgpt.com đang có TRONG PHIÊN — gồm cả cookie máy chủ vừa Set-Cookie.

    Lọc theo miền chứ không lấy cả rổ: phiên có đi qua cdn.oaistatic.com và các miền
    phụ của OpenAI, nhét cookie miền khác vào kho chatgpt.com là gửi trả sai địa chỉ."""
    out = {}
    try:
        jar = session.cookies.jar
    except Exception:                                    # noqa: BLE001 - phiên giả/đã đóng
        return out
    try:
        for c in jar:
            dom = (getattr(c, "domain", "") or "").lstrip(".")
            if dom and dom != "chatgpt.com" and not dom.endswith(".chatgpt.com"):
                continue
            ten, gia = getattr(c, "name", ""), getattr(c, "value", "")
            if ten and gia:
                out[str(ten)] = str(gia)
    except Exception:                                    # noqa: BLE001
        return {}
    return out


def _bo_kieu_phien_trong_jar(session, giu_manh):
    """Xoá khỏi jar của phiên đang chạy mọi cookie phiên KHÁC kiểu đang giữ. Trả số
    cookie đã thấy (0 = jar vốn sạch)."""
    try:
        jar = session.cookies.jar
        bo = [c for c in list(jar)
              if store.la_ho_phien(getattr(c, "name", ""))
              and ((getattr(c, "name", "") != store.COOKIE_BAT_BUOC) != bool(giu_manh))]
        for c in bo:
            try:
                jar.clear(c.domain, c.path, c.name)
            except Exception:                            # noqa: BLE001
                pass
        return len(bo)
    except Exception:                                    # noqa: BLE001 - phiên giả/đã đóng
        return 0


def _bo_cookie_hoi_thoai_trong_jar(session):
    """Xoá cookie theo từng cuộc trò chuyện (conv_key_/history_off_<uuid>) khỏi jar."""
    try:
        jar = session.cookies.jar
        for c in [c for c in list(jar)
                  if not store.bo_cookie_rac({getattr(c, "name", ""): "x"})]:
            try:
                jar.clear(c.domain, c.path, c.name)
            except Exception:                            # noqa: BLE001
                pass
    except Exception:                                    # noqa: BLE001 - phiên giả/đã đóng
        pass


def _ghi_cookie_ve_kho(acc_id, session, ua=None, on_log=None):
    """Gộp cookie máy chủ vừa cấp về kho. Trả VÂN TAY mới, hoặc None nếu không có gì đổi.

    Đây là nửa "ghi ngược" của phần hâm nóng (xem đầu file). Ba điều cố ý:

      * Chỉ gửi phần ĐÃ ĐỔI cho ``save_account`` — hàm đó vốn gộp đè, nên cookie tiện
        ích từng đẩy mà lượt này máy chủ không nhắc tới vẫn còn nguyên trong kho.
      * Cookie máy chủ XOÁ (Set-Cookie hết hạn) thì curl đã bỏ khỏi jar, tức là nó vắng
        mặt ở đây và kho giữ nguyên bản cũ — không tự tay xoá cookie của người dùng.
      * Không có gì đổi thì KHÔNG ghi: mỗi lần ghi là một lần ``updated`` nhảy, mà giao
        diện đọc con số đó để nói "cookie mới cách đây N phút".

    Mọi lỗi đều nuốt: đây là việc phụ, không được phép làm hỏng lô dịch đang chạy."""
    try:
        # Cookie theo từng cuộc trò chuyện không bao giờ được ghi về kho (xem
        # chatgpt_cookie_store.COOKIE_THEO_HOI_THOAI): mỗi lượt hỏi đẻ thêm một cặp.
        # Dọn cả khỏi jar của phiên đang chạy: curl_cffi dựng lại cookie từ jar trước MỖI
        # request, nên một phiên sống suốt lượt A→Z dài cũng phình tới mức mất phiên.
        _bo_cookie_hoi_thoai_trong_jar(session)
        moi = store.bo_cookie_rac(_cookie_cua_session(session))
        if not moi:
            return None
        rec = store.get_account(acc_id) or {}
        cu = rec.get("cookies") or {}
        doi = {k: v for k, v in moi.items() if cu.get(k) != v}
        if not doi:
            return None
        doi_phien = [k for k in doi if store.la_ho_phien(k)]
        if doi_phien:
            # Máy chủ vừa CẤP LẠI cookie phiên. Kho nay THAY cả họ phiên khi nhận (xem
            # Kho.save_account), nên phải gửi ĐỦ họ theo đúng KIỂU máy chủ vừa đặt — mảnh
            # `.N` hay tên trần — chứ không chỉ phần đổi, kẻo mảnh không đổi bị rụng. Kiểu
            # kia là đồ cũ: lệnh xoá của máy chủ có thể không trúng bản ta tự đặt vào jar
            # lúc dựng phiên, để lại một BỘ TRỘN mà máy chủ nối thành rác (05/10/2026: 6
            # tài khoản "chết" vì đúng lý do này). Dọn luôn kiểu cũ khỏi jar.
            giu_manh = any(k != store.COOKIE_BAT_BUOC for k in doi_phien)
            doi = {k: v for k, v in doi.items() if not store.la_ho_phien(k)}
            doi.update({k: v for k, v in _tach_kieu_phien(moi, giu_manh).items()
                        if store.la_ho_phien(k)})
            # Jar còn kiểu cũ = phiên này đang gửi bộ trộn. Trả None ở cuối để bên gọi
            # KHÔNG đồng bộ vân tay -> lượt sau dựng lại phiên từ kho đã sạch (thư viện
            # curl có thể giữ bản riêng của cookie, xoá trong jar chưa chắc đủ).
            jar_tron = _bo_kieu_phien_trong_jar(session, giu_manh) > 0
        else:
            jar_tron = False
        # save_account() dựng id từ slug(nhãn); nhãn nào slug ra id khác thì dùng thẳng
        # id, kẻo tự đẻ ra một bản ghi thứ hai cho cùng một tài khoản.
        nhan = rec.get("label") or acc_id
        if store.slug(nhan) != acc_id:
            nhan = acc_id
        store.save_account(nhan, doi, source="app tự hâm", ua=ua or rec.get("ua"))
        if on_log:
            on_log("    [chatgpt-web] hâm nóng '%s': %d cookie mới (%s)"
                   % (acc_id, len(doi), ", ".join(sorted(doi)[:4])))
        gop = dict(cu)
        if doi_phien:
            gop = {k: v for k, v in gop.items() if not store.la_ho_phien(k)}
        gop.update(doi)
        return None if jar_tron else _van_tay(gop)
    except Exception as e:                               # noqa: BLE001
        # Hàm này bị gọi trong 'finally' của ask(): ném ra từ đây là NUỐT MẤT lỗi thật
        # của lô dịch. Kể cả on_log của bên gọi hỏng cũng không được thoát ra.
        try:
            if on_log:
                on_log("    [chatgpt-web] không ghi được cookie mới về kho: %s" % e)
        except Exception:                                # noqa: BLE001
            pass
        return None


def _ham_phien(acc_id, p, on_log=None):
    """Ghi ngược cookie của một phiên rồi ĐỒNG BỘ vân tay của chính phiên đó.

    Không đồng bộ vân tay thì lượt sau đọc kho thấy cookie 'lạ' (chính bản mình vừa
    ghi) và dựng lại phiên từ đầu — mỗi lô một lần bắt tay TLS + xin token, tốn vô ích."""
    vt = _ghi_cookie_ve_kho(acc_id, p.session, ua=getattr(p, "ua", None), on_log=on_log)
    if vt:
        try:
            p.van_tay = vt
        except Exception:                                # noqa: BLE001
            pass
    return vt


def _build_lock(acc_id):
    with _PHIEN_LOCK:
        lk = _PHIEN_BUILD_LOCKS.get(acc_id)
        if lk is None:
            lk = _PHIEN_BUILD_LOCKS[acc_id] = threading.Lock()
        return lk


def _dong_phien(p):
    try:
        p.session.close()
    except Exception:                                    # noqa: BLE001
        pass


def _loai_phien(acc_id, expected=None):
    with _PHIEN_LOCK:
        p = _PHIEN.get(acc_id)
        if p is None or (expected is not None and p is not expected):
            return
        _PHIEN.pop(acc_id, None)
    _dong_phien(p)


def _phien(acc_id, timeout=TIMEOUT_MAC_DINH, lam_moi=False):
    """Lấy (hoặc dựng) phiên của một tài khoản. Cookie đổi -> dựng lại tự động."""
    cookies, ua = _doc_cookie(acc_id)
    vt = _van_tay(cookies)
    with _PHIEN_LOCK:
        p = _PHIEN.get(acc_id)
        if p is not None and p.van_tay == vt and not lam_moi:
            return p
    with _build_lock(acc_id):
        with _PHIEN_LOCK:
            p = _PHIEN.get(acc_id)
            if p is not None and p.van_tay == vt and not lam_moi:
                return p
            cu = _PHIEN.pop(acc_id, None)
        if cu is not None:
            _dong_phien(cu)
        # oai-device-id giữ nguyên theo tài khoản để phía OpenAI không thấy "thiết bị
        # mới" ở mỗi lô; lấy từ cookie nếu tiện ích đẩy được oai-did.
        did = cookies.get("oai-did") or str(uuid.uuid4())
        moi = _Phien(_tao_session(cookies, ua), vt,
                     threading.Semaphore(max(1, CONCURRENCY)), ua, did)
        with _PHIEN_LOCK:
            _PHIEN[acc_id] = moi
        return moi


def _xep_hang(sem, timeout, stop_event, han_cho=SESSION_QUEUE_TIMEOUT, on_wait=None):
    """Chờ tới lượt tài khoản, vẫn nghe nút Dừng. Trả False nếu quá hạn chờ."""
    han = max(1.0, min(float(timeout or han_cho), float(han_cho)))
    bat_dau = time.monotonic()
    lan_bao = 0.0
    while True:
        if stop_event is not None and stop_event.is_set():
            raise ChatGPTWebStopped()
        if sem.acquire(timeout=0.25):
            return True
        troi = time.monotonic() - bat_dau
        if troi >= han:
            return False
        if on_wait is not None and troi - lan_bao >= 15:
            lan_bao = troi
            on_wait(troi, han)


# --------------------------------------------------------------------------- #
#  Bốn bước gọi
# --------------------------------------------------------------------------- #
def _loi_theo_ma(status, body, buoc):
    """Dịch mã HTTP + thân trả lời sang loại lỗi bộ điều phối hiểu."""
    t = (body or "")[:600]
    thap = t.lower()
    if status in (401,):
        return ChatGPTWebAuth("%s: 401 — cookie hết hạn, hãy đăng nhập lại chatgpt.com "
                              "rồi bấm 'Gửi vào app'." % buoc)
    if status == 403:
        if "just a moment" in thap or "cf-chl" in thap or "cloudflare" in thap:
            return ChatGPTWebBlocked(
                "%s: Cloudflare chặn. Cookie cf_clearance đã cũ hoặc User-Agent không "
                "khớp — mở chatgpt.com trong Chrome cho qua trang kiểm tra, rồi bấm "
                "'Gửi vào app' lấy cookie mới." % buoc)
        if "unusual activity" in thap or "access denied" in thap:
            return ChatGPTWebBlocked("%s: OpenAI chặn tạm tài khoản/IP — %s" % (buoc, t[:200]))
        return ChatGPTWebBlocked("%s: 403 — %s" % (buoc, t[:200]))
    if status == 429:
        return ChatGPTWebQuota("%s: 429 — hết lượt/hãm tốc: %s" % (buoc, t[:200]))
    if status in (500, 502, 503, 504, 520, 522, 524):
        return ChatGPTWebFlaky("%s: máy chủ %d — %s" % (buoc, status, t[:120]), cho=5.0)
    return ChatGPTWebError("%s: HTTP %d — %s" % (buoc, status, t[:200]))


def _mo_trang(p, timeout):
    """BƯỚC 2 — lấy 'dpl' và một đường dẫn .js thật để nhét vào cấu hình proof-of-work.
    Hỏng thì bỏ qua: proof vẫn dựng được, chỉ là kém giống trình duyệt hơn."""
    if p.dpl:
        return
    try:
        r = p.session.get(BASE + "/", timeout=min(30, timeout))
        html = r.text or ""
    except Exception:                                    # noqa: BLE001
        return
    m = re.search(r"dpl-[0-9a-f]{20,}", html)
    if m:
        p.dpl = m.group(0)
    m = re.search(r"(?:https://cdn\.oaistatic\.com/)?_next/static/[^\"'\s]+?\.js", html)
    if m:
        p.script = m.group(0)


def _lay_token(p, timeout, buoc_lai=False):
    """BƯỚC 1 — accessToken của phiên đăng nhập.

    403 ở NGAY ĐẦU PHIÊN có thể chỉ là màn chào hỏi của Cloudflare, không phải phán
    quyết. ĐO 28/08/2026, phiên mới tinh dựng từ cookie kho, gọi /api/auth/session liên
    tiếp trên CÙNG một phiên:

        403, 403, 200, 200      lặp 3/3 lần y hệt (kho chưa có cookie máy chủ trả về)
        403, 200, 200           2/2 lần, sau khi đã ghi ngược cookie một lượt
        200, 200, 200           3/3 tài khoản khác, đo lại 30/08, cùng máy cùng IP

    Tức là NGẮT QUÃNG chứ không phải nết cố định — đừng đọc đoạn này thành "phiên mới
    luôn ăn 403". Cái chắc chắn là: trong cửa sổ đo được ấy, chính trang 403 đó
    Set-Cookie ``oai-did`` / ``oai-hlib`` / ``_account``, có chúng rồi thì lượt sau qua;
    và mọi lượt 403 đều tự khỏi trong vòng ba request trên cùng một phiên.

    Bản trước bắn ChatGPTWebBlocked ngay ở 403 đầu tiên, mà Blocked thì ask() DỪNG HẲN
    không thử lại — nên trong cửa sổ đó mọi phiên mới đều chết ở request đầu, lại kèm
    câu lỗi đổ cho cookie ("mở chatgpt.com rồi gửi lại cookie") nên rất khó lần ra. Nay
    thử lại trong CÙNG phiên vài lượt rồi mới kết luận: bị chặn thật thì vẫn ra Blocked,
    chỉ tốn thêm hai request."""
    if p.token and not buoc_lai and (time.time() - p.token_luc) < TOKEN_SONG_GIAY:
        return p.token
    han = time.monotonic() + max(1.0, float(timeout or 60))
    r = None
    for lan in range(max(1, LAP_LAI_403)):
        try:
            r = p.session.get(BASE + "/api/auth/session",
                              headers={"accept": "application/json"},
                              timeout=min(60, timeout))
        except Exception as e:                           # noqa: BLE001
            raise ChatGPTWebFlaky("bước 1 (auth/session) lỗi mạng: %s" % e, cho=3.0)
        if r.status_code != 403 or lan + 1 >= LAP_LAI_403 or time.monotonic() >= han:
            break
        time.sleep(CHO_LAI_403_GIAY)
    if r.status_code != 200:
        raise _loi_theo_ma(r.status_code, r.text, "bước 1 (auth/session)")
    try:
        data = r.json()
    except Exception:                                    # noqa: BLE001
        raise ChatGPTWebAuth(
            "bước 1 (auth/session): máy chủ không trả JSON — nhiều khả năng đang bị "
            "Cloudflare chặn. Mở chatgpt.com trong Chrome rồi gửi lại cookie.")
    tok = (data or {}).get("accessToken")
    if not tok:
        raise ChatGPTWebAuth(
            "bước 1 (auth/session): không có accessToken (chưa đăng nhập hoặc cookie "
            "phiên đã hết hạn) — hãy đăng nhập chatgpt.com rồi bấm 'Gửi vào app'.")
    p.token, p.token_luc = tok, time.time()
    return tok


def _headers(p, them=None):
    h = {
        "authorization": "Bearer " + (p.token or ""),
        "accept": "*/*",
        "content-type": "application/json",
        "oai-device-id": p.device_id,
        "oai-language": "en-US",
        "origin": BASE,
        "referer": BASE + "/",
    }
    if them:
        h.update(them)
    return h


def _yeu_cau_chat(p, timeout):
    """BƯỚC 3 — xin token phiên chat + đề bài proof-of-work."""
    proof = _requirements_token(p.ua, p.dpl, p.script)
    try:
        r = p.session.post(BASE + "/backend-api/sentinel/chat-requirements",
                           headers=_headers(p), json={"p": proof},
                           timeout=min(90, timeout))
    except Exception as e:                               # noqa: BLE001
        raise ChatGPTWebFlaky("bước 3 (chat-requirements) lỗi mạng: %s" % e, cho=3.0)
    if r.status_code != 200:
        raise _loi_theo_ma(r.status_code, r.text, "bước 3 (chat-requirements)")
    try:
        data = r.json() or {}
    except Exception:                                    # noqa: BLE001
        raise ChatGPTWebBlocked(
            "bước 3 (chat-requirements): trả về không phải JSON — thường là trang chặn "
            "của Cloudflare. Lấy lại cookie từ Chrome rồi thử lại.")
    # CỐ Ý KHÔNG dừng ở cờ turnstile.required.
    #
    # Bản đầu (25/08/2026) thấy cờ này là ném ChatGPTWebBlocked ngay, không thử bước 4.
    # ĐO trên kho thật của người dùng: 7/7 tài khoản đều báo y hệt một câu — mà 7 tài
    # khoản khác nhau cùng "bị chặn" giống hệt nhau thì đó là CỜ MẶC ĐỊNH của máy chủ,
    # không phải phán quyết riêng cho từng tài khoản. Dừng ở đây là TỰ ĐOÁN hộ máy chủ
    # rồi báo cáo lời đoán như một sự thật, và không bao giờ biết bước 4 có chạy hay không.
    #
    # Nay cứ đi tiếp và để CHÍNH máy chủ trả lời. Nếu bước 4 bị 403 thật thì lúc đó mới
    # kết luận là Turnstile chặn — kèm theo cờ này làm bằng chứng (xem _hoi_mot_luot).
    if not data.get("token"):
        raise ChatGPTWebError("bước 3 (chat-requirements): thiếu token phiên chat.")
    return data


def _tom_tat_yeu_cau(data):
    """Một dòng ngắn mô tả máy chủ đang ĐÒI gì — nhét vào câu lỗi của bước 4 để đọc log
    là biết ngay vướng chỗ nào, khỏi phải bật thêm chế độ gỡ lỗi."""
    tur = (data or {}).get("turnstile") or {}
    pow_ = (data or {}).get("proofofwork") or {}
    phan = []
    if tur.get("required"):
        phan.append("turnstile=CÓ ĐÒI")
    if pow_.get("required"):
        phan.append("pow=CÓ ĐÒI(difficulty=%s)" % (pow_.get("difficulty") or "?"))
    if (data or {}).get("persona"):
        phan.append("persona=%s" % data["persona"])
    return ", ".join(phan) or "không đòi gì thêm"


def _proof_cho(p, data):
    pw = (data or {}).get("proofofwork") or {}
    if not pw.get("required"):
        return None
    return _proof_token(pw.get("seed") or "", pw.get("difficulty") or "",
                        p.ua, p.dpl, p.script)


# --------------------------------------------------------------------------- #
#  Đọc stream SSE
#
#  ChatGPT web trả về HAI khuôn khác nhau tuỳ lúc, nên đọc CẢ HAI:
#    (a) khuôn đầy đủ : mỗi sự kiện chứa nguyên message -> parts[0] là bản DỒN sẵn.
#    (b) khuôn delta  : sự kiện đầu 'add' cả message, các sự kiện sau chỉ 'append' thêm
#                       một mẩu chữ (có/không kèm đường dẫn 'p').
#  Bắt sót một khuôn thì kết quả rỗng mà không có lỗi nào — đúng kiểu hỏng khó tìm nhất.
# --------------------------------------------------------------------------- #
_DUONG_CHU = "/message/content/parts/0"


def _tim_model_slug(o, sau=0):
    """metadata.resolved_model_slug / model_slug ở bất kỳ tầng nào của một sự kiện SSE."""
    if sau > 6:
        return None
    if isinstance(o, dict):
        md = o.get("metadata")
        if isinstance(md, dict):
            for k in ("resolved_model_slug", "model_slug"):
                if isinstance(md.get(k), str) and md[k]:
                    return md[k]
        for v in o.values():
            if isinstance(v, (dict, list)):
                r = _tim_model_slug(v, sau + 1)
                if r:
                    return r
    elif isinstance(o, list):
        for v in o:
            r = _tim_model_slug(v, sau + 1)
            if r:
                return r
    return None


class _Gom:
    """Gom các mẩu SSE thành một chuỗi chữ.

    HAI THỨ PHẢI LỌC, cả hai đều đã cắn thật:

    1. **Bản sao CÂU HỎI.** Stream mở đầu bằng chính message của NGƯỜI DÙNG
       (``author.role == "user"``) rồi mới tới câu trả lời. Bản đầu không xét vai nên
       nhặt luôn bản sao câu hỏi; ĐO 25/08/2026 bằng ``--check acc0``: hỏi "Trả lời đúng
       một từ: OK" thì nhận về nguyên văn "Trả lời đúng một từ: OK" chứ không phải "OK".
       Với một lô dịch thì hậu quả nặng hơn nhiều — câu hỏi (nguyên lô tiếng Trung + luật
       dịch) DÀI HƠN câu trả lời, nên luật "bản nào dài hơn thì thắng" của bản đầu sẽ ném
       bản dịch đi và giữ lại đúng cái prompt.

    2. **Phần suy nghĩ.** Model đời gpt-5.x trả thêm message ``content_type`` là
       ``thoughts``/``reasoning_recap``. Đó không phải bản dịch.

    Nên gom theo TỪNG message có id riêng, chỉ giữ message VĂN BẢN của TRỢ LÝ, và lấy
    message hợp lệ CUỐI CÙNG — không so độ dài nữa.
    """

    def __init__(self):
        self._bai = {}            # id message -> chữ (dict giữ thứ tự chèn)
        self._id_hien = None      # message đang nhận các mẩu 'append' ngầm
        self.conversation_id = None
        self.loi = None
        # Model THẬT đã trả lời (metadata.model_slug). Gửi 'auto' mà hết lượt model lớn thì
        # OpenAI hạ cấp âm thầm — chỉ trường này nói ra (đo 02/10/2026).
        self.model = None

    @property
    def chu(self):
        for mid in reversed(list(self._bai)):
            if self._bai[mid]:
                return self._bai[mid]
        return ""

    @staticmethod
    def _la_bai_tro_ly(msg):
        """Message này có phải VĂN BẢN của trợ lý không?

        Vai thiếu hẳn thì vẫn nhận (khuôn lạ/rút gọn), nhưng vai ghi rõ là user/system/
        tool thì loại — đó chính là bản sao câu hỏi."""
        vai = (msg.get("author") or {}).get("role")
        if vai is not None and vai != "assistant":
            return False
        kieu = (msg.get("content") or {}).get("content_type")
        return kieu in (None, "text")

    def _dat(self, mid, s):
        # Khuôn (a) gửi bản DỒN SẴN cho cùng một id -> ghi đè là đúng, khỏi so độ dài.
        if isinstance(s, str):
            self._bai[mid] = s

    def _them(self, s):
        if not isinstance(s, str):
            return
        if self._id_hien is None:
            # Có mẩu 'append' mà chưa thấy message nào mở đầu: vẫn gom (khuôn rút gọn),
            # nhưng để riêng một ô chứ không dính vào bài của message khác.
            self._id_hien = "?"
            self._bai.setdefault("?", "")
        self._bai[self._id_hien] = self._bai.get(self._id_hien, "") + s

    def su_kien(self, obj):
        if isinstance(obj, str):                 # 'v1' của dòng delta_encoding
            return
        if not isinstance(obj, dict):
            return
        if obj.get("error") or obj.get("detail"):
            self.loi = obj.get("error") or obj.get("detail")
            return
        if obj.get("conversation_id"):
            self.conversation_id = obj["conversation_id"]
        slug = _tim_model_slug(obj)
        if slug:
            self.model = slug

        # ---- khuôn (a): nguyên message ----
        msg = obj.get("message")
        if isinstance(msg, dict):
            if not self._la_bai_tro_ly(msg):
                # Bản sao câu hỏi / phần suy nghĩ: bỏ qua, VÀ ngắt 'message đang nhận'
                # để các mẩu append sau đó không chảy nhầm vào đây.
                self._id_hien = None
                return
            mid = msg.get("id") or "?"
            self._id_hien = mid
            parts = (msg.get("content") or {}).get("parts") or []
            if parts and isinstance(parts[0], str):
                self._dat(mid, parts[0])
            else:
                self._bai.setdefault(mid, "")
            return

        # ---- khuôn (b): delta ----
        if "v" not in obj:
            return
        o, duong, v = obj.get("o"), obj.get("p"), obj.get("v")
        if o == "patch" and isinstance(v, list):
            for con in v:
                self.su_kien(con)
            return
        if o == "add" and duong in ("", None) and isinstance(v, dict):
            self.su_kien(v)
            return
        if o in (None, "append"):
            if duong in (None, "", _DUONG_CHU) or str(duong).endswith("/parts/0"):
                self._them(v)
            return
        if o == "replace" and str(duong or "").endswith("/parts/0"):
            if self._id_hien is not None:
                self._dat(self._id_hien, v)


def _doc_stream(r, deadline, stop_event, gom):
    for dong in r.iter_lines():
        if stop_event is not None and stop_event.is_set():
            raise ChatGPTWebStopped()
        if time.monotonic() > deadline:
            raise ChatGPTWebTimeout("stream quá hạn giữa chừng")
        if not dong:
            continue
        if isinstance(dong, bytes):
            dong = dong.decode("utf-8", "replace")
        if not dong.startswith("data:"):
            continue
        than = dong[5:].strip()
        if not than or than == "[DONE]":
            if than == "[DONE]":
                break
            continue
        try:
            gom.su_kien(json.loads(than))
        except ValueError:
            continue


def _xoa_hoi_thoai(p, conversation_id, timeout=15):
    """Ẩn đoạn chat vừa tạo. Best-effort, hỏng thì kệ — không phải việc chính."""
    if not (XOA_HOI_THOAI and conversation_id):
        return
    try:
        p.session.patch(BASE + "/backend-api/conversation/" + conversation_id,
                        headers=_headers(p), json={"is_visible": False},
                        timeout=timeout)
    except Exception:                                    # noqa: BLE001
        pass


def _hoi_mot_luot(p, prompt, model, timeout, stop_event):
    """BƯỚC 4 — gửi câu hỏi, gom stream, trả CHỮ."""
    deadline = time.monotonic() + max(1.0, float(timeout))
    yeu_cau = _yeu_cau_chat(p, timeout)
    proof = _proof_cho(p, yeu_cau)
    h = _headers(p, {
        "accept": "text/event-stream",
        "openai-sentinel-chat-requirements-token": yeu_cau.get("token") or "",
    })
    if proof:
        h["openai-sentinel-proof-token"] = proof

    lech = -int(round((time.altzone if time.daylight and time.localtime().tm_isdst
                       else time.timezone) / 60))
    than = {
        "action": "next",
        "messages": [{
            "id": str(uuid.uuid4()),
            "author": {"role": "user"},
            "create_time": time.time(),
            "content": {"content_type": "text", "parts": [prompt]},
            "metadata": {"serialization_metadata": {"custom_symbol_offsets": []}},
        }],
        "parent_message_id": str(uuid.uuid4()),
        "model": model or MODEL_MAC_DINH,
        "timezone_offset_min": -lech,
        "history_and_training_disabled": True,
        "conversation_mode": {"kind": "primary_assistant"},
        "force_paragen": False,
        "force_rate_limit": False,
        "websocket_request_id": str(uuid.uuid4()),
    }

    gom = _Gom()
    try:
        r = p.session.post(BASE + "/backend-api/conversation", headers=h, json=than,
                           stream=True, timeout=max(1.0, deadline - time.monotonic()))
    except Exception as e:                               # noqa: BLE001
        raise ChatGPTWebFlaky("bước 4 (conversation) lỗi mạng: %s" % e, cho=3.0)
    try:
        if r.status_code != 200:
            than_loi = r.text
            tur = (yeu_cau.get("turnstile") or {}).get("required")
            if r.status_code == 403 and tur:
                # ĐẾN ĐÂY mới được kết luận Turnstile chặn: máy chủ đã thật sự từ chối,
                # chứ không phải ta đoán từ một cái cờ ở bước 3.
                raise ChatGPTWebBlocked(
                    "OpenAI từ chối lượt gọi và có đòi Turnstile — đường cookie không "
                    "qua được cho tài khoản này. Hãy mở chatgpt.com trong Chrome, chat "
                    "tay một câu cho qua kiểm tra rồi gửi lại cookie; vẫn vậy thì dùng "
                    "nguồn dịch khác. [%s] %s"
                    % (_tom_tat_yeu_cau(yeu_cau), (than_loi or "")[:150]))
            raise _loi_theo_ma(
                r.status_code, than_loi,
                "bước 4 (conversation) [%s]" % _tom_tat_yeu_cau(yeu_cau))
        _doc_stream(r, deadline, stop_event, gom)
    finally:
        try:
            r.close()
        except Exception:                                # noqa: BLE001
            pass

    if gom.loi:
        raise ChatGPTWebError("bước 4 (conversation): %s" % str(gom.loi)[:200])
    _xoa_hoi_thoai(p, gom.conversation_id)
    p.model_vua_dung = gom.model
    return gom.chu


def _lay_models(p, timeout=30):
    """Danh sách model tài khoản đang được dùng — chỉ để hiện lên nút Kiểm tra."""
    try:
        r = p.session.get(BASE + "/backend-api/models", headers=_headers(p),
                          timeout=timeout)
        if r.status_code != 200:
            return []
        return [m.get("slug") for m in (r.json() or {}).get("models") or []
                if m.get("slug")]
    except Exception:                                    # noqa: BLE001
        return []


def list_model_info(account_id, timeout=90, lam_moi=False):
    """Danh sách model của tài khoản, cùng chữ ký với ``gemini_web_client``.

    Ở đây web KHÔNG cho biết tên hiển thị hay mô tả nên nhãn = chính tên model; giao
    diện dùng chung một đường cho cả hai nguồn cookie."""
    ok, vi_sao = available()
    if not ok:
        return {"ok": False, "kind": "missing", "msg": vi_sao, "models": [],
                "trang_thai": ""}
    try:
        p = _phien(account_id, timeout=timeout, lam_moi=lam_moi)
    except Exception as e:                               # noqa: BLE001
        return dict(_check_error_result(e), trang_thai="")
    if not p.models:
        p.models = _lay_models(p)
    ds = [{"id": m, "name": m, "display": m, "desc": "", "available": True,
           "advanced": False, "nhan": m} for m in (p.models or [])]
    if not ds:
        return {"ok": False, "kind": "error", "trang_thai": "", "models": [],
                "msg": "phiên không trả về danh sách model nào"}
    return {"ok": True, "kind": "ok", "trang_thai": "", "models": ds,
            "msg": "%d model" % len(ds)}


def model_manh_nhat(ds):
    """Bản số cao nhất, bỏ mini/nano: ['gpt-5-5','gpt-5-6','gpt-5-6-mini','auto'] -> 'gpt-5-6'.
    Không có model nào mang số -> None (bên gọi để 'auto')."""
    tot, khoa_tot = None, None
    for m in ds or []:
        s = str(m).lower()
        if "mini" in s or "nano" in s:
            continue
        so = tuple(int(x) for x in re.findall(r"\d+", s))
        if so and (khoa_tot is None or so > khoa_tot):
            tot, khoa_tot = m, so
    return tot


def xep_model_manh_yeu(ds):
    """Model chat chuẩn xếp MẠNH -> YẾU: bản thường trước mini, mini trước nano; trong
    mỗi bậc số phiên bản cao trước. ['gpt-5-5','gpt-5-6','gpt-5-6-mini','research','auto']
    -> ['gpt-5-6','gpt-5-5','gpt-5-6-mini']."""
    hop = []
    for m in ds or []:
        mo = _MAU_MODEL_CHUAN.match(str(m).strip())
        if not mo:
            continue
        bac = {"": 0, "mini": 1, "nano": 2}[(mo.group(1) or "").lower()]
        so = [int(x) for x in re.findall(r"\d+", str(m))]
        # Số âm + phần tử chặn cuối: phiên bản DÀI hơn (gpt-5-6) đứng trước bản ngắn
        # cùng gốc (gpt-5), và 5-6 trước 5-5.
        hop.append((bac, [-x for x in so] + [1], str(m).strip()))
    hop.sort(key=lambda x: (x[0], x[1]))
    return [m for _b, _s, m in hop]


def _model_dang_nghi(acc_id, model):
    with _MODEL_NGHI_LOCK:
        han = _MODEL_NGHI.get((acc_id, model))
        if han is None:
            return False
        if time.time() >= han:
            _MODEL_NGHI.pop((acc_id, model), None)
            return False
        return True


def _cho_model_nghi(acc_id, model, giay):
    with _MODEL_NGHI_LOCK:
        _MODEL_NGHI[(acc_id, model)] = time.time() + float(giay)


def _chuoi_model(p, ten, acc_id):
    """Danh sách model sẽ thử LẦN LƯỢT cho một lượt hỏi, luôn kết thúc bằng 'auto'.

    'tot-nhat' -> mọi model chat chuẩn của tài khoản, mạnh tới yếu, bỏ model đang nghỉ
    (đã hết lượt/lỗi trên CHÍNH tài khoản này). Tên khác -> đúng model đó rồi 'auto',
    y như trước."""
    ten = (ten or "").strip()
    ds = []
    if ten.lower() == MODEL_TOT_NHAT:
        if not p.models:
            p.models = _lay_models(p)
        ds = xep_model_manh_yeu(p.models)
    if not ds:
        ds = [_chon_model(p, ten)]
    if ds[-1] != MODEL_MAC_DINH:
        ds.append(MODEL_MAC_DINH)
    return [m for m in ds if m == MODEL_MAC_DINH or not _model_dang_nghi(acc_id, m)]


def _chon_model(p, ten):
    """Web đặt tên model khác API và mỗi tài khoản có danh sách riêng, nên tên người
    dùng gõ chỉ là GỢI Ý: soi từ khoá trong danh sách THẬT của tài khoản; không khớp
    thì để 'auto' cho OpenAI tự chọn."""
    ten = (ten or "").strip()
    if not ten or ten.lower() in ("auto", "mac-dinh", "mặc định"):
        return MODEL_MAC_DINH
    if not p.models:
        p.models = _lay_models(p)
    if ten.lower() == MODEL_TOT_NHAT:
        return model_manh_nhat(p.models) or MODEL_MAC_DINH
    if not p.models:
        return ten
    thap = ten.lower()
    for m in p.models:
        if m.lower() == thap:
            return m
    for m in p.models:
        if thap in m.lower() or m.lower() in thap:
            return m
    return MODEL_MAC_DINH


# --------------------------------------------------------------------------- #
#  API công khai — chữ ký trùng gemini_web_client
# --------------------------------------------------------------------------- #
def ask(account_id, prompt, model=None, timeout=TIMEOUT_MAC_DINH, retries=3,
        stop_event=None, on_log=None, temporary=True):
    """Hỏi ChatGPT web 1 lượt, trả về CHỮ. Ném ChatGPTWeb* khi hỏng.

    temporary=True: bật history_and_training_disabled — không lưu vào lịch sử tài khoản
    và không dính ngữ cảnh lượt trước, đúng thứ bộ dịch cần (mỗi lô là một lệnh độc lập).
    """
    if stop_event is not None and stop_event.is_set():
        raise ChatGPTWebStopped()
    ok, vi_sao = available()
    if not ok:
        raise ChatGPTWebMissing(vi_sao)

    loi_cuoi = None
    lam_moi = False
    p = None
    seconds = max(0.05, float(timeout or TIMEOUT_MAC_DINH))
    deadline = time.monotonic() + seconds

    def con_lai():
        con = deadline - time.monotonic()
        if con <= 0:
            raise ChatGPTWebTimeout(
                "quá hạn %ss cho nguyên lô của '%s'" % (int(round(seconds)), account_id))
        return con

    for lan in range(1, max(1, int(retries)) + 1):
        if stop_event is not None and stop_event.is_set():
            raise ChatGPTWebStopped()
        try:
            p = _phien(account_id, timeout=con_lai(), lam_moi=lam_moi)
            remaining = con_lai()
            if not _xep_hang(
                    p.sem, remaining, stop_event, han_cho=remaining,
                    on_wait=(lambda troi, han:
                             on_log("    [chatgpt-web] tài khoản '%s' vẫn bận %.0fs/%.0fs…"
                                    % (account_id, troi, han))
                             if on_log else None)):
                raise ChatGPTWebTimeout(
                    "chờ quá deadline %ss tới lượt tài khoản '%s'"
                    % (int(round(seconds)), account_id))
            try:
                _lay_token(p, con_lai(), buoc_lai=lam_moi)
                _mo_trang(p, con_lai())
                # Gói Free chỉ có VÀI lượt model đầu bảng (đo 02/10/2026: xin gpt-5-6 ->
                # "You've hit your limit"). Hạ NGAY trên chính phiên này sang model KẾ
                # TIẾP trong chuỗi (06/10/2026: trước đây nhảy thẳng về 'auto' = mini) —
                # thay vì nghỉ rồi nện lại model đã cạn.
                ds_thu = _chuoi_model(p, model, account_id)
                ten_model = ds_thu[0]
                raw = None
                for i, ten_model in enumerate(ds_thu):
                    try:
                        raw = _hoi_mot_luot(p, prompt, ten_model, con_lai(), stop_event)
                        break
                    except ChatGPTWebError as e:
                        het = _la_het_luot_model(e)
                        loi_may_chu = (isinstance(e, ChatGPTWebFlaky)
                                       and re.search(r"máy chủ 5\d\d", str(e)) is not None)
                        if (i + 1 >= len(ds_thu) or ten_model == MODEL_MAC_DINH
                                or not (het or loi_may_chu)):
                            raise
                        _cho_model_nghi(account_id, ten_model,
                                        HET_LUOT_NGHI_GIAY if het else MODEL_LOI_NGHI_GIAY)
                        if on_log:
                            on_log("    [chatgpt-web] '%s' %s %s → thử %s%s"
                                   % (account_id, ten_model,
                                      "hết lượt" if het else "lỗi máy chủ",
                                      ds_thu[i + 1],
                                      " (nghỉ model này %.0f giờ)"
                                      % (HET_LUOT_NGHI_GIAY / 3600) if het else ""))
            finally:
                p.sem.release()
                # Ghi ngược NGAY CẢ KHI lượt này hỏng: vé Cloudflare và token phiên máy
                # chủ vừa cấp vẫn tốt, vứt đi thì lần sau lại phải mở tab Chrome.
                _ham_phien(account_id, p, on_log=on_log)
            if not raw:
                raise ChatGPTWebFlaky("trả lời rỗng (có thể đang bị hãm tốc)", cho=8.0)
            if _la_loi_soan_san(raw):
                raise ChatGPTWebFlaky("web trả câu lỗi soạn sẵn: %s" % raw[:80])
            # Báo model nào trả lời khi XIN ĐÍCH DANH một model, hoặc khi máy chủ âm thầm
            # trả bằng model KHÁC cái vừa xin. Chuỗi 'tot-nhat' chạy đều thì im lặng —
            # nó là mặc định của đường dịch, mỗi lô một dòng thì ngập log; chỗ chuỗi hạ
            # bậc đã có dòng báo riêng ở trên.
            tra_loi = getattr(p, "model_vua_dung", None)
            dich_danh = (model or "").strip().lower() not in ("", MODEL_TOT_NHAT,
                                                              MODEL_MAC_DINH)
            if (on_log and tra_loi and ten_model != MODEL_MAC_DINH
                    and (dich_danh or tra_loi != ten_model)):
                on_log("    [chatgpt-web] '%s' xin %s → trả lời bởi %s%s"
                       % (account_id, ten_model, tra_loi,
                          "" if tra_loi == ten_model else "  ⚠ BỊ HẠ CẤP"))
            return raw
        except (ChatGPTWebStopped, ChatGPTWebMissing):
            raise
        except ChatGPTWebTimeout as e:
            loi_cuoi = e
            break
        except ChatGPTWebFlaky as e:
            # Phiên vẫn tốt -> KHÔNG dựng lại phiên, chỉ nghỉ rồi gọi lại.
            loi_cuoi = e
            if lan >= retries:
                break
            cho = min(45.0, getattr(e, "cho", 2.0) * lan)
            if on_log:
                on_log("    [chatgpt-web] %s → nghỉ %.0fs rồi gọi lại (%d/%d)"
                       % (e, cho, lan, retries))
            for _ in range(int(cho * 2)):            # ngủ nhưng vẫn nghe nút Dừng
                if stop_event is not None and stop_event.is_set():
                    raise ChatGPTWebStopped()
                time.sleep(0.5)
            continue
        except ChatGPTWebQuota:
            raise                                   # để pool xoay tài khoản ngay
        except ChatGPTWebBlocked:
            raise                                   # nện tiếp chỉ tổ bị chặn lâu hơn
        except ChatGPTWebAuth as e:
            # Cookie có thể vừa được tiện ích đẩy bản mới: thử dựng lại phiên MỘT lần.
            loi_cuoi = e
            if lam_moi:
                _loai_phien(account_id, expected=p)
                raise
            lam_moi = True
            if on_log:
                on_log("    [chatgpt-web] cookie hỏng — dựng lại phiên bằng cookie mới nhất…")
            continue
        except Exception as e:                       # noqa: BLE001
            loi_cuoi = e if isinstance(e, ChatGPTWebError) else ChatGPTWebError(str(e))
            if lan < retries:
                cho = min(20, 3 * lan)
                if on_log:
                    on_log("    [chatgpt-web] %s → nghỉ %ds rồi thử lại (%d/%d)"
                           % (loi_cuoi, cho, lan, retries))
                for _ in range(int(cho * 2)):
                    if stop_event is not None and stop_event.is_set():
                        raise ChatGPTWebStopped()
                    time.sleep(0.5)
                lam_moi = True
    # Timeout/stream đứt/auth cuối cùng chứng minh transport này không còn đáng tái sử
    # dụng. Không drop với Flaky (rỗng/câu lỗi soạn sẵn): lỗi nội dung, socket vẫn tốt.
    if (p is not None and loi_cuoi is not None and not isinstance(
            loi_cuoi, (ChatGPTWebFlaky, ChatGPTWebQuota, ChatGPTWebBlocked))):
        _loai_phien(account_id, expected=p)
    raise loi_cuoi or ChatGPTWebError("không gọi được ChatGPT web")


def list_accounts():
    """Tài khoản cookie đang có (không kèm giá trị cookie)."""
    return store.list_accounts()


def _check_error_kind(error):
    if isinstance(error, ChatGPTWebAuth):
        return "auth"
    if isinstance(error, ChatGPTWebQuota):
        return "quota"
    if isinstance(error, ChatGPTWebBlocked):
        return "blocked"
    if isinstance(error, ChatGPTWebMissing):
        return "missing"
    return "error"


def _check_error_result(error, models=None):
    if not isinstance(error, ChatGPTWebError):
        error = ChatGPTWebError(str(error))
    return {
        "ok": False,
        "kind": _check_error_kind(error),
        "msg": str(error),
        "models": list(models or []),
    }


def check(account_id, timeout=120, stop_event=None):
    """Làm nóng một phiên rồi hỏi một câu ngắn; không đóng phiên đang dịch."""
    if stop_event is not None and stop_event.is_set():
        raise ChatGPTWebStopped()
    ok, vi_sao = available()
    if not ok:
        return {"ok": False, "kind": "missing", "msg": vi_sao, "models": []}
    t0 = time.time()
    try:
        p = _phien(account_id, timeout=timeout, lam_moi=False)
    except Exception as e:                              # noqa: BLE001
        return _check_error_result(e)
    try:
        raw = ask(account_id, "Trả lời đúng một từ: OK", timeout=timeout, retries=1,
                  stop_event=stop_event)
    except ChatGPTWebStopped:
        raise
    except Exception as e:                              # noqa: BLE001
        return _check_error_result(e, p.models)
    # Danh sách model chỉ để hiện lên bảng kết quả "Kiểm tra tất cả". Hỏi SAU khi đã gọi
    # được một lượt thật: hỏi trước mà cookie hỏng thì chỉ tổ thêm một request vô ích.
    if not p.models:
        p.models = _lay_models(p)
    elapsed = time.time() - t0
    return {
        "ok": True,
        "kind": "ok",
        "msg": "trả lời: %s (%.1fs)" % (raw[:40], elapsed),
        "models": p.models,
        # Giữ cùng hình dạng với gemini_web_client để ô chọn model đổ được từ kết quả.
        "model_info": [{"id": m, "name": m, "display": m, "desc": "",
                        "available": True, "advanced": False, "nhan": m}
                       for m in (p.models or [])],
        "elapsed": elapsed,
    }


def check_all(account_ids=None, timeout=120, max_workers=6, on_result=None,
              stop_event=None):
    """Kiểm tra/làm nóng toàn bộ kho, song song theo tài khoản và đánh dấu cookie trùng.

    Bản ghi trùng cookie phiên không được gọi lần hai: đó là cùng một phiên, vừa tốn
    lượt vừa không tạo thêm làn hay hạn mức. Kết quả vẫn có đủ một dòng cho mỗi bản ghi.
    """
    source_ids = store.account_ids() if account_ids is None else account_ids
    ids = list(dict.fromkeys(source_ids))
    if stop_event is not None and stop_event.is_set():
        raise ChatGPTWebStopped()
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
            except Exception:                            # noqa: BLE001
                pass

    workers = max(1, min(int(max_workers or 1), len(leaders) or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check, acc_id, timeout, stop_event): acc_id
                   for acc_id in leaders}
        for future in concurrent.futures.as_completed(futures):
            acc_id = futures[future]
            try:
                result = future.result()
            except ChatGPTWebStopped:
                raise
            except Exception as e:                       # noqa: BLE001
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
        })

    rows = [results[acc_id] for acc_id in ids]
    return {
        "total": len(rows),
        "live": sum(1 for row in rows if row.get("kind") == "ok"),
        "failed": sum(1 for row in rows if row.get("kind") not in ("ok", "duplicate")),
        "duplicates": sum(1 for row in rows if row.get("kind") == "duplicate"),
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
            raise ChatGPTWebStopped()
        try:
            kq = check(row["id"], timeout=min(float(timeout or 90), 90.0),
                       stop_event=stop_event)
        except ChatGPTWebStopped:
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
    return tuple((acc_id, (accounts.get(acc_id) or {}).get("updated") or 0)
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
        waiter.wait()
        force = False

    try:
        report = check_all(ids, timeout=timeout, max_workers=max_workers,
                           on_result=on_result, stop_event=stop_event)
        report = dict(report)
        report = _kiem_lai_tung_cai(report, timeout, stop_event)
        report["usable_accounts"] = [row["id"] for row in report.get("results") or []
                                     if row.get("kind") == "ok"]
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


# --------------------------------------------------------------------------- #
#  Luồng "ngáp đều" — nửa còn lại của phần hâm nóng (xem đầu file)
# --------------------------------------------------------------------------- #
_HAM_LOCK = threading.Lock()
_HAM_LUONG = None
_HAM_DUNG = threading.Event()

# Tài khoản hỏng liên tiếp -> nghỉ hâm cho tới khi kho có bản ghi MỚI (tiện ích đẩy
# sang). Không có mốc này thì một tài khoản đã đăng xuất sẽ bị gõ cửa mãi mãi.
_HAM_HONG = {}                        # acc_id -> (số lần hỏng liên tiếp, mốc 'updated')
HAM_HONG_TOI_DA = 3

# Lượt ngáp đầu tiên chờ ngắn thôi: cookie vừa đẩy có thể đã gần hết hạn, đợi trọn một
# chu kỳ là mất luôn cái đang còn cứu được. Nhưng cũng không gọi ngay lúc app khởi động.
HAM_CHO_DAU_GIAY = 30.0


def ham_nong_mot(acc_id, timeout=60, on_log=None):
    """Một lượt ngáp cho MỘT tài khoản: xin lại bước 1 rồi ghi cookie về kho.

    Tài khoản đang bận dịch thì BỎ QUA chứ không xếp hàng: lô dịch đó tự hâm hộ rồi,
    chen vào chỉ làm lô sau phải đợi."""
    p = _phien(acc_id, timeout=timeout)
    if not p.sem.acquire(blocking=False):
        return False
    try:
        _lay_token(p, timeout, buoc_lai=True)
    finally:
        p.sem.release()
        _ham_phien(acc_id, p, on_log=on_log)
    return True


def _vong_ham_nong(phut, on_log):
    cho = max(60.0, float(phut) * 60.0)
    dau = True
    while not _HAM_DUNG.wait(HAM_CHO_DAU_GIAY if dau else cho):
        dau = False
        try:
            # CHỈ hâm tài khoản người dùng tự đặt tên (07/09/2026): vòng này gọi mạng
            # THẬT dưới danh nghĩa từng tài khoản, hâm cái đã bỏ quên là tốn lượt vô ích.
            # Cùng luật với mọi chỗ chọn cookie khác; named_account_ids() tự trả lại
            # nguyên danh sách nếu lọc ra rỗng nên kho không tên vẫn được hâm như cũ.
            ids = store.named_account_ids(store.account_ids())
        except Exception:                                # noqa: BLE001 - kho hỏng/đang ghi
            continue
        for acc_id in ids:
            if _HAM_DUNG.is_set():
                return
            try:
                rec = store.get_account(acc_id) or {}
                if not store.da_dang_nhap(rec.get("cookies") or {}):
                    continue
                hong, moc = _HAM_HONG.get(acc_id, (0, None))
                if hong >= HAM_HONG_TOI_DA and moc == (rec.get("updated") or 0):
                    continue
                ham_nong_mot(acc_id, on_log=on_log)
                _HAM_HONG.pop(acc_id, None)
            except ChatGPTWebStopped:
                return
            except Exception as e:                       # noqa: BLE001
                # Mốc đọc LẠI sau khi hỏng: lượt vừa rồi có thể đã ghi ngược được vài
                # cookie, so với mốc cũ thì vòng sau tưởng có bản mới và thử lại ngay.
                moc_moi = (store.get_account(acc_id) or {}).get("updated") or 0
                hong = _HAM_HONG.get(acc_id, (0, None))[0] + 1
                _HAM_HONG[acc_id] = (hong, moc_moi)
                if hong == HAM_HONG_TOI_DA and on_log:
                    on_log("    [chatgpt-web] hâm nóng '%s' hỏng %d lần (%s) — nghỉ tới "
                           "khi tiện ích đẩy cookie mới." % (acc_id, hong, e))


def bat_ham_nong(on_log=None, phut=None):
    """Bật luồng hâm nóng nền. Gọi bao nhiêu lần cũng được — chỉ một luồng cho cả tiến
    trình. Trả True nếu luồng đang chạy sau lời gọi này."""
    global _HAM_LUONG
    p = HAM_NONG_PHUT if phut is None else float(phut)
    if p <= 0 or not available()[0]:
        return False
    with _HAM_LOCK:
        if _HAM_LUONG is not None and _HAM_LUONG.is_alive():
            return True
        _HAM_DUNG.clear()
        _HAM_LUONG = threading.Thread(target=_vong_ham_nong, args=(p, on_log),
                                      name="chatgpt-web-ham-nong", daemon=True)
        _HAM_LUONG.start()
    return True


def tat_ham_nong():
    global _HAM_LUONG
    _HAM_DUNG.set()
    with _HAM_LOCK:
        t, _HAM_LUONG = _HAM_LUONG, None
    if t is not None and t.is_alive():
        t.join(timeout=2)


def dang_ham_nong():
    with _HAM_LOCK:
        return _HAM_LUONG is not None and _HAM_LUONG.is_alive()


def close_all():
    tat_ham_nong()
    with _PHIEN_LOCK:
        ps = list(_PHIEN.values())
        _PHIEN.clear()
        _PHIEN_BUILD_LOCKS.clear()
    for p in ps:
        _dong_phien(p)


# --------------------------------------------------------------------------- #
#  CLI gỡ lỗi — chạy được mà không cần mở GUI
# --------------------------------------------------------------------------- #
def _cli(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Thử ChatGPT web bằng cookie.")
    ap.add_argument("--list", action="store_true", help="Liệt kê tài khoản trong kho.")
    ap.add_argument("--check", metavar="ACC", help="Kiểm tra 1 tài khoản.")
    ap.add_argument("--check-all", action="store_true", help="Kiểm tra cả kho.")
    ap.add_argument("--ask", nargs=2, metavar=("ACC", "PROMPT"), help="Hỏi 1 câu.")
    ap.add_argument("--warm", metavar="ACC", nargs="?", const="*",
                    help="Hâm nóng 1 tài khoản (bỏ trống = cả kho): xin lại phiên rồi "
                         "ghi cookie mới về kho, đúng việc luồng nền vẫn làm.")
    ap.add_argument("--model", default=MODEL_MAC_DINH)
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args(argv)

    ok, vi_sao = available()
    if not ok:
        print(vi_sao)
        return 2
    if a.warm:
        ids = store.account_ids() if a.warm == "*" else [a.warm]
        for acc_id in ids:
            try:
                xong = ham_nong_mot(acc_id, timeout=a.timeout,
                                    on_log=lambda s: print(s, flush=True))
                print("· %-16s %s" % (acc_id, "xong" if xong else "đang bận, bỏ qua"))
            except Exception as e:                       # noqa: BLE001
                print("· %-16s HỎNG: %s" % (acc_id, e))
        return 0
    if a.list or not (a.check or a.check_all or a.ask):
        for x in list_accounts():
            print("· %-16s %2d cookie  cf_clearance:%s  %4.1f phút trước"
                  % (x["id"], x["so_cookie"], "có" if x["co_cf"] else "KHÔNG",
                     x["tuoi_giay"] / 60.0))
    if a.check:
        print(json.dumps(check(a.check, timeout=a.timeout), ensure_ascii=False, indent=1))
    if a.check_all:
        print(json.dumps(check_all(timeout=a.timeout), ensure_ascii=False, indent=1))
    if a.ask:
        print(ask(a.ask[0], a.ask[1], model=a.model, timeout=a.timeout, retries=1,
                  on_log=lambda s: print(s, flush=True)))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
