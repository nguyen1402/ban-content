# -*- coding: utf-8 -*-
"""Kho COOKIE dùng chung + máy chủ nhỏ nhận cookie từ tiện ích trình duyệt.

Vì sao tách ra: app đang có HAI nguồn dịch bằng cookie — gemini.google.com và
chatgpt.com — mà phần "nhận cookie từ tiện ích, gộp vào kho, xoay tài khoản" của
hai bên GIỐNG HỆT nhau. Chỉ khác đúng bốn thứ:

    * tên file kho          (gemini_cookies.json / chatgpt_cookies.json)
    * cookie BẮT BUỘC       (__Secure-1PSID / __Secure-next-auth.session-token)
    * cổng nghe             (8785 / 8786 — bán-content; CapCut TTS Studio giữ 8765 / 8766)
    * trang phải đăng nhập  (để câu báo lỗi nói đúng chỗ người dùng cần mở)

Nên phần chung nằm ở lớp ``Kho`` trong file này; hai module
``gemini_cookie_store.py`` và ``chatgpt_cookie_store.py`` chỉ còn là mặt tiền trỏ
vào một thể hiện ``Kho``. Mọi tên hàm/hành vi công khai của bản Gemini GIỮ NGUYÊN —
đây là bước tách, không phải bước đổi luật.

AN TOÀN (giữ nguyên như bản Gemini): máy chủ chỉ nghe 127.0.0.1 (không ra mạng
ngoài) và chỉ nhận POST có ``Origin: chrome-extension://…`` — trang web bình thường
không đẩy rác vào được. File kho nằm ở %LOCALAPPDATA%\\BanContent (NGOÀI repo) nên
cookie không lọt vào git.
"""

import hashlib
import json
import os
import re
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler


def store_dir():
    """Thư mục kho (ngoài repo). 14/10/2026 user: bán-content dùng kho RIÊNG %LOCALAPPDATA%\\BanContent — độc lập với
    CapCut TTS Studio (kho %LOCALAPPDATA%\\CapCutTTS). Đặt biến môi trường BAN_CONTENT_DATA để đổi chỗ."""
    if os.environ.get("BAN_CONTENT_DATA"):
        d = os.environ["BAN_CONTENT_DATA"]
    else:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        d = os.path.join(base, "BanContent")
    os.makedirs(d, exist_ok=True)
    return d


def kho_chung_capcut(ten_file):
    """Đường dẫn kho cookie của CapCut TTS Studio nếu máy này có (dùng chung), không có -> None."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    p = os.path.join(base, "CapCutTTS", ten_file)
    return p if os.path.isfile(p) else None


# Tài khoản RIÊNG của một tab (vd tab 🛡 Đăng YouTube an toàn: cookie người dùng dán tay,
# id 'rieng.dang-yt'). Mọi DANH SÁCH tài khoản — xoay vòng của tab Dịch, tiền kiểm, ô danh
# sách cookie — bỏ qua chúng; chỉ bên gọi đích danh id mới dùng được (get_account vẫn trả).
# Thêm 17/09/2026. Trước đó chưa id nào mang tiền tố này nên kho đang có không đổi hành vi.
TIEN_TO_RIENG = "rieng."


def slug(label):
    s = re.sub(r"[^A-Za-z0-9_.-]+", "-", (label or "").strip()).strip("-")
    return s or "acc"


def _giong_nhan_tu_sinh(nhan):
    """'acc-' + đuôi token ngẫu nhiên (xem gemini_cookie_ext/background.js: 8 ký tự cuối
    của cookie phiên, bỏ ký tự không phải chữ/số) — có cả chữ hoa lẫn chữ thường."""
    m = re.fullmatch(r"acc-([A-Za-z0-9]{5,8})", (nhan or "").strip())
    if not m:
        return False
    duoi = m.group(1)
    return any(c.isupper() for c in duoi) and any(c.islower() for c in duoi)


class Kho:
    """Một kho cookie của MỘT dịch vụ.

    ten_file        : tên file JSON trong thư mục kho.
    env_path        : biến môi trường cho phép trỏ file kho đi chỗ khác (test dùng).
    cookie_bat_buoc : thiếu cookie này thì coi như chưa đăng nhập.
    port            : cổng mặc định của máy chủ nhận cookie.
    trang_dang_nhap : ghi vào câu báo lỗi để người dùng biết phải mở trang nào.
    co_cookie       : các cờ tóm tắt cho giao diện, dạng ((tên_cờ, tên_cookie), …).
    ten_luong       : tên luồng máy chủ (chỉ để dễ đọc khi soi luồng).
    """

    def __init__(self, ten_file, env_path, cookie_bat_buoc, port,
                 trang_dang_nhap, co_cookie=(), ten_luong="cookie-server",
                 ten_tien_ich="gemini_cookie_ext", phien_xoay=False, bo_ten_cookie=None):
        # phien_xoay=True: cookie phiên của dịch vụ này ĐỔI liên tục (ChatGPT/NextAuth —
        # app tự hâm nóng là ghi token mới vào kho), nên không dựng lại được nhãn tự sinh
        # từ cookie hiện tại. Xem nhan_tu_sinh().
        self.phien_xoay = bool(phien_xoay)
        # bo_ten_cookie: regex tên cookie KHÔNG được giữ trong kho (cookie theo từng cuộc
        # trò chuyện của ChatGPT). None = giữ mọi cookie, y như cũ.
        self.bo_ten_cookie = re.compile(bo_ten_cookie) if bo_ten_cookie else None
        self.ten_file = ten_file
        self.env_path = env_path
        self.cookie_bat_buoc = cookie_bat_buoc
        self.port = int(port)
        self.trang_dang_nhap = trang_dang_nhap
        self.co_cookie = tuple(co_cookie)
        self.ten_luong = ten_luong
        self.ten_tien_ich = ten_tien_ich
        self._lock = threading.RLock()

    # ---------------------------------------------------------------- #
    #  File kho
    # ---------------------------------------------------------------- #
    def store_path(self):
        # Đọc biến môi trường ở MỖI lượt gọi (không cache): test đổi biến sau khi
        # import module vẫn phải trỏ đúng file tạm.
        if os.environ.get(self.env_path):
            return os.environ[self.env_path]
        # 14/10/2026 user: "hiện tại cứ cho nó 1 chỗ nạp chung, phòng hờ sau chuyển máy" -> máy CÓ kho của CapCut TTS
        # Studio thì dùng CHUNG kho đó (nạp một chỗ); máy không có (chuyển máy, chỉ cài bán-content) mới dùng kho RIÊNG
        # %LOCALAPPDATA%\BanContent + tiện ích cookie_ext. BAN_CONTENT_DATA đặt thì luôn dùng kho riêng.
        chung = kho_chung_capcut(self.ten_file)
        if chung and not os.environ.get("BAN_CONTENT_DATA"):
            return chung
        return os.path.join(store_dir(), self.ten_file)

    def load_store(self):
        """Đọc kho; hỏng/chưa có -> kho rỗng (không ném lỗi ra ngoài)."""
        p = self.store_path()
        if not os.path.isfile(p):
            return {"version": 1, "accounts": {}}
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or not isinstance(data.get("accounts"), dict):
                return {"version": 1, "accounts": {}}
            return data
        except (OSError, ValueError):
            return {"version": 1, "accounts": {}}

    def _save_store(self, data):
        """Ghi ĐÈ nguyên tử: ghi file tạm rồi thay tên, để lần đọc song song không thấy
        file vá dở (tiện ích đẩy 5 phút/lần trong khi bộ dịch đang đọc)."""
        p = self.store_path()
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, p)

    # ---------------------------------------------------------------- #
    #  Cookie phiên — có thể bị CHIA MẢNH
    # ---------------------------------------------------------------- #
    def gia_tri_phien(self, cookies):
        """Giá trị cookie phiên; tự ghép lại nếu trình duyệt đã chia mảnh.

        ĐO ĐƯỢC 25/08/2026 trên chatgpt.com: kho không nhận tài khoản dù đã đăng nhập,
        vì trình duyệt KHÔNG có cookie tên ``__Secure-next-auth.session-token`` mà có
        hai cookie ``…session-token.0`` và ``…session-token.1``. Đây là nết của
        NextAuth/Auth.js: token JWT vượt trần ~4096 byte của MỘT cookie thì nó cắt thành
        ``<tên>.0``, ``<tên>.1``, … Trình duyệt gửi đủ các mảnh, máy chủ tự ghép theo số
        thứ tự — nên phía mình cũng chỉ cần GỬI ĐỦ MẢNH, không phải ghép trước khi gửi.

        Hai chỗ bắt buộc phải dùng hàm này thay vì tra thẳng tên cookie:
          * xét "đã đăng nhập chưa" (nếu không thì tài khoản chunk bị từ chối oan),
          * vân tay phiên để dò bản ghi trùng (phải là chuỗi ĐÃ GHÉP thì hai bản ghi của
            cùng một phiên mới nhận ra nhau).
        """
        ck = cookies or {}
        nguyen = ck.get(self.cookie_bat_buoc)
        if nguyen:
            return nguyen
        tien_to = self.cookie_bat_buoc + "."
        manh = []
        for ten, gt in ck.items():
            if not ten.startswith(tien_to):
                continue
            duoi = ten[len(tien_to):]
            if duoi.isdigit():
                manh.append((int(duoi), gt))
        # Sắp theo SỐ thứ tự, không phải theo chữ: 10 phải đứng sau 9.
        return "".join(gt for _, gt in sorted(manh)) if manh else ""

    def la_ho_phien(self, ten):
        """Cookie này thuộc HỌ cookie phiên: tên trần hoặc một mảnh `<tên>.<số>`."""
        ten = str(ten or "")
        if ten == self.cookie_bat_buoc:
            return True
        tien_to = self.cookie_bat_buoc + "."
        return ten.startswith(tien_to) and ten[len(tien_to):].isdigit()

    def bo_cookie_rac(self, cookies):
        """Bỏ cookie không được giữ trong kho (bo_ten_cookie). Trả dict mới."""
        if self.bo_ten_cookie is None:
            return dict(cookies or {})
        return {k: v for k, v in (cookies or {}).items()
                if not self.bo_ten_cookie.search(str(k))}

    def phien_bi_tron(self, cookies):
        """True khi bộ cookie có CẢ kiểu liền lẫn kiểu chia mảnh của cookie phiên.

        Máy chủ NextAuth gom MỌI cookie bắt đầu bằng tên phiên rồi nối lại, nên bộ trộn
        thành chuỗi rác -> "không có accessToken" dù từng nửa vẫn sống (đo 05/10/2026 trên
        6 tài khoản ChatGPT thật: nguyên trạng hỏng 6/6, tách riêng từng kiểu sống 6/6)."""
        ck = cookies or {}
        lien = self.cookie_bat_buoc in ck
        manh = any(self.la_ho_phien(k) and k != self.cookie_bat_buoc for k in ck)
        return lien and manh

    def da_dang_nhap(self, cookies):
        return bool(self.gia_tri_phien(cookies))

    # ---------------------------------------------------------------- #
    #  Tài khoản
    # ---------------------------------------------------------------- #
    def save_account(self, label, cookies, source="extension", ua=None):
        """Ghi/cập nhật 1 tài khoản. Trả (account_id, số cookie đã lưu).

        Cookie mới GỘP đè lên cookie cũ chứ không thay sạch: có lúc trình duyệt chỉ đẩy
        được vài cookie (đang xoay), gộp thì phần chưa đổi của phiên cũ vẫn còn nguyên."""
        if not isinstance(cookies, dict):
            raise ValueError("Cookie phải là một đối tượng JSON {tên: giá trị}.")
        acc_id = slug(label)
        with self._lock:
            data = self.load_store()
            cu = data["accounts"].get(acc_id) or {}
            gop = dict(cu.get("cookies") or {})
            moi_ck = {str(k): str(v) for k, v in cookies.items() if v}
            # Lượt đẩy có cookie PHIÊN thì nó là bản ĐẦY ĐỦ của phiên: bỏ hết họ cookie
            # phiên cũ rồi mới gộp. Gộp đè từng tên (bản cũ) để lại mảnh/kiểu cũ — vd kho
            # đang giữ '…session-token' liền mà trình duyệt gửi '.0' + '.1' — thành bộ
            # trộn, máy chủ nối cả ba thành rác và tài khoản "chết" dù cookie vừa gửi còn
            # sống. Gửi lại bao nhiêu lần cũng không chữa được (người dùng 05/10/2026).
            if any(self.la_ho_phien(k) for k in moi_ck):
                gop = {k: v for k, v in gop.items() if not self.la_ho_phien(k)}
            gop.update(moi_ck)
            gop = self.bo_cookie_rac(gop)
            # Xét cookie BẮT BUỘC trên bộ ĐÃ GỘP: lượt đẩy thiếu cookie phiên (trình
            # duyệt đang xoay cookie) vẫn dùng được nếu tài khoản cũ đã có, chỉ chặn khi
            # CẢ HAI cùng không có — tức là thật sự chưa đăng nhập.
            # Chấp cả dạng bị chia mảnh `<tên>.0/.1/…` — xem gia_tri_phien().
            if not self.da_dang_nhap(gop):
                raise ValueError("Thiếu cookie %s (kể cả dạng chia mảnh %s.0/.1) — "
                                 "chưa đăng nhập %s?"
                                 % (self.cookie_bat_buoc, self.cookie_bat_buoc,
                                    self.trang_dang_nhap))
            moi = {
                "label": label or acc_id,
                "cookies": gop,
                "updated": time.time(),
                "source": source,
                "ua": ua or cu.get("ua"),
            }
            # Đóng dấu nhãn TỰ SINH ngay lúc nhận (nhãn = 'acc-' + đuôi chính cookie phiên
            # vừa gửi) và GIỮ dấu qua mọi lượt cập nhật sau: cookie phiên ChatGPT xoay
            # liên tục, để tới lúc lọc mới dựng lại thì không còn khớp (đo 02/10/2026).
            if cu.get("tu_sinh") or (label and slug(label) == slug(
                    self.nhan_tu_cookie({str(k): str(v) for k, v in cookies.items() if v}))):
                moi["tu_sinh"] = True
            data["accounts"][acc_id] = moi
            self._save_store(data)
        return acc_id, len(gop)

    def thay_cookie(self, acc_id, cookies, source="app chữa phiên trộn"):
        """Thay NGUYÊN bộ cookie của một bản ghi (không gộp) — để chữa bộ phiên bị trộn
        hoặc dọn cookie rác. Giữ nhãn/dấu tự sinh/ua; không có bản ghi thì không làm gì.
        Trả True nếu đã ghi."""
        with self._lock:
            data = self.load_store()
            rec = data["accounts"].get(acc_id)
            if rec is None or not self.da_dang_nhap(cookies):
                return False
            rec = dict(rec)
            rec["cookies"] = self.bo_cookie_rac(
                {str(k): str(v) for k, v in cookies.items() if v})
            rec["updated"] = time.time()
            rec["source"] = source
            data["accounts"][acc_id] = rec
            self._save_store(data)
            return True

    def luu_tru_va_xoa(self, acc_id, ly_do=""):
        """Chuyển bản ghi sang file LƯU TRỮ '<kho>.da_xoa.json' rồi xoá khỏi kho.

        Dùng cho nút "Kiểm tra tất cả": tài khoản vẫn hỏng xác thực sau khi đã kiểm lại
        một mình nó thì bỏ khỏi kho (người dùng 06/10/2026: "key bị lỗi thì xóa nó đi").
        Cố ý KHÔNG xoá mất hẳn: sáng cùng ngày 6 tài khoản từng báo hỏng mà thật ra còn
        sống (lỗi kho trộn cookie, đã sửa) — nhầm thì vẫn lấy lại được từ file lưu trữ,
        hoặc bấm 'Gửi vào app' ở Chrome là bản ghi tự có lại. Trả True nếu đã xoá."""
        with self._lock:
            data = self.load_store()
            rec = data["accounts"].get(acc_id)
            if rec is None:
                return False
            p = self.store_path() + ".da_xoa.json"
            try:
                with open(p, "r", encoding="utf-8") as f:
                    kho_xoa = json.load(f)
                if not isinstance(kho_xoa, dict):
                    kho_xoa = {}
            except (OSError, ValueError):
                kho_xoa = {}
            kho_xoa[acc_id] = dict(rec, da_xoa_luc=time.time(), ly_do_xoa=str(ly_do)[:200])
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(kho_xoa, f, ensure_ascii=False, indent=1)
            os.replace(tmp, p)
            data["accounts"].pop(acc_id, None)
            self._save_store(data)
            return True

    def delete_account(self, acc_id):
        with self._lock:
            data = self.load_store()
            mat = data["accounts"].pop(acc_id, None)
            if mat is not None:
                self._save_store(data)
            return mat is not None

    def get_account(self, acc_id):
        """Trả bản ghi tài khoản (có cookie) hoặc None."""
        return self.load_store()["accounts"].get(acc_id)

    @staticmethod
    def account_ids_from_store(accounts):
        """Sắp id theo độ mới từ một snapshot kho đã đọc sẵn (bỏ tài khoản RIÊNG)."""
        return sorted((k for k in accounts if not k.startswith(TIEN_TO_RIENG)),
                      key=lambda k: -(accounts[k].get("updated") or 0))

    def account_ids(self):
        """Danh sách id tài khoản, tài khoản MỚI CẬP NHẬT đứng trước."""
        return self.account_ids_from_store(self.load_store()["accounts"])

    def duplicate_account_groups(self, account_ids=None):
        """Nhóm các bản ghi có cùng cookie phiên chính, không làm lộ giá trị cookie.

        Đây chỉ bắt được bản ghi trùng CHÍNH XÁC cookie phiên. Hai hồ sơ trình duyệt
        đăng nhập cùng một tài khoản nhưng có hai phiên khác nhau vẫn có thể dùng chung
        hạn mức mà không thể nhận diện chắc chắn chỉ từ cookie.
        """
        data = self.load_store()["accounts"]
        ordered = (self.account_ids_from_store(data) if account_ids is None
                   else list(account_ids))
        groups = {}
        for acc_id in ordered:
            rec = data.get(acc_id) or {}
            sid = self.gia_tri_phien(rec.get("cookies"))
            if not sid:
                continue
            fingerprint = hashlib.sha256(sid.encode("utf-8")).hexdigest()
            groups.setdefault(fingerprint, []).append(acc_id)
        return [ids for ids in groups.values() if len(ids) > 1]

    def unique_account_ids(self, ids=None):
        """Giữ một làn cho mỗi cookie phiên giống hệt nhau, ưu tiên id đứng trước."""
        ordered = self.account_ids() if ids is None else list(dict.fromkeys(ids))
        duplicates = {
            acc_id
            for group in self.duplicate_account_groups(ordered)
            for acc_id in group[1:]
        }
        return [acc_id for acc_id in ordered if acc_id not in duplicates]

    def nhan_tu_sinh(self, acc_id, rec=None):
        """Nhãn của tài khoản này do KHO tự đặt, hay do người dùng đặt?

        Không đoán theo mẫu chữ ('acc-...' người dùng cũng gõ được) mà DỰNG LẠI đúng
        nhãn tự sinh từ chính cookie phiên của bản ghi rồi so. Cookie phiên
        (`cookie_bat_buoc`) ổn định theo tài khoản — Google chỉ xoay cookie phụ — nên
        phép so này ra cùng kết quả ở mọi lần chạy.
        """
        if rec is None:
            rec = self.load_store()["accounts"].get(acc_id) or {}
        nhan = rec.get("label") or acc_id
        if rec.get("tu_sinh"):
            return True
        if slug(nhan) == slug(self.nhan_tu_cookie(rec.get("cookies") or {})):
            return True
        # Bản ghi CŨ của kho cookie xoay (ChatGPT), nhận từ trước khi có dấu 'tu_sinh':
        # cookie đã đổi nên phép dựng lại ở trên trượt — cả ba nhãn tự sinh trong kho
        # thật lọt hết (acc-YkYViraw / acc-D5BhFxQ / acc-kduny30Q, đo 02/10/2026). Nhận
        # theo HÌNH DẠNG tiện ích sinh ra: 'acc-' + 5–8 ký tự là đuôi token ngẫu nhiên,
        # tức lẫn cả chữ HOA lẫn chữ thường. Tên gõ tay kiểu 'acc-12345678', 'acc-cua-toi'
        # không khớp nên vẫn giữ. Kho cookie ổn định (Gemini) không đi nhánh này.
        return self.phien_xoay and _giong_nhan_tu_sinh(nhan)

    def named_account_ids(self, ids=None):
        """Chỉ giữ tài khoản NGƯỜI DÙNG tự đặt tên (bỏ nhãn tự sinh 'acc-<id phiên>').

        Lọc sạch trơn thì TRẢ LẠI NGUYÊN danh sách: kho toàn nhãn tự sinh mà lọc thành
        rỗng là hỏng cả lượt chạy, tệ hơn hẳn việc dùng vài tài khoản không tên.
        """
        accounts = self.load_store()["accounts"]
        ordered = self.account_ids() if ids is None else list(dict.fromkeys(ids))
        giu = [k for k in ordered
               if not self.nhan_tu_sinh(k, accounts.get(k) or {})]
        return giu or ordered

    def list_accounts(self):
        """Danh sách tóm tắt để hiện lên giao diện — KHÔNG kèm giá trị cookie."""
        accs = self.load_store()["accounts"]
        out = []
        for k in self.account_ids():
            a = accs[k]
            ck = a.get("cookies") or {}
            row = {
                "id": k,
                "label": a.get("label") or k,
                "updated": a.get("updated") or 0,
                "tuoi_giay": max(0.0, time.time() - (a.get("updated") or 0)),
                "so_cookie": len(ck),
                "source": a.get("source") or "",
            }
            for ten_co, ten_cookie in self.co_cookie:
                # Cờ của chính cookie phiên phải xét cả dạng chia mảnh, kẻo giao diện
                # báo "KHÔNG có" trên một tài khoản đang chạy tốt.
                row[ten_co] = bool(self.gia_tri_phien(ck)
                                   if ten_cookie == self.cookie_bat_buoc
                                   else ck.get(ten_cookie))
            out.append(row)
        return out

    def nhan_tu_cookie(self, cookies):
        sid = self.gia_tri_phien(cookies)
        return ("acc-" + re.sub(r"[^A-Za-z0-9]", "", sid[-8:])) if sid else "acc-trong"

    def import_json(self, text, label=None):
        """Nhận JSON dán tay từ nút 'Sao chép JSON' của tiện ích (hoặc từ file).

        Chấp cả 3 dạng: {"label":…, "cookies":{…}} / {"cookies":{…}} / {tên: giá trị}."""
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError("JSON phải là một đối tượng.")
        cookies = obj.get("cookies") if isinstance(obj.get("cookies"), dict) else obj
        nhan = label or obj.get("label") or self.nhan_tu_cookie(cookies)
        return self.save_account(nhan, cookies, source="dan-tay")


# --------------------------------------------------------------------------- #
#  Máy chủ nhận cookie từ tiện ích
# --------------------------------------------------------------------------- #
def tao_handler(kho):
    """Sinh lớp handler gắn với MỘT kho. Mỗi kho một cổng nên mỗi kho một lớp riêng —
    không dùng biến toàn cục để hai máy chủ (Gemini/ChatGPT) không giẫm lên nhau."""

    class _Handler(BaseHTTPRequestHandler):
        server_version = "BanContentCookie/1.0"
        on_log = None                     # gán từ ngoài: hàm log(str)
        _kho = kho

        def _tra(self, code, obj, origin=None):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.end_headers()
            self.wfile.write(body)

        def _origin_ok(self):
            """CHỈ nhận request từ TIỆN ÍCH. Trang web thường có Origin https://… nên bị
            chặn ở đây; cổng lại chỉ mở trên 127.0.0.1 nên máy khác không với tới."""
            o = self.headers.get("Origin") or ""
            return o.startswith("chrome-extension://") or o.startswith("moz-extension://")

        def do_OPTIONS(self):
            ok = self._origin_ok()
            self._tra(204 if ok else 403, {},
                      origin=(self.headers.get("Origin") if ok else None))

        def do_GET(self):
            if self.path.startswith("/status"):
                # Cho tiện ích/GUI kiểm tra "app có đang nghe không" — không trả cookie.
                self._tra(200, {"ok": True, "msg": "CapCut TTS đang nhận cookie",
                                "accounts": [a["id"] for a in self._kho.list_accounts()]},
                          origin=(self.headers.get("Origin") if self._origin_ok() else None))
            else:
                self._tra(404, {"ok": False, "msg": "Không có đường dẫn này"})

        def do_POST(self):
            o = self.headers.get("Origin") or ""
            if not self._origin_ok():
                self._tra(403, {"ok": False, "msg": "Chỉ nhận từ tiện ích trình duyệt"})
                return
            if not self.path.startswith("/cookies"):
                self._tra(404, {"ok": False, "msg": "Không có đường dẫn này"}, origin=o)
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n > 0 else b""
                obj = json.loads(raw.decode("utf-8"))
                acc_id, so = self._kho.save_account(
                    obj.get("label"), obj.get("cookies") or {},
                    source="extension", ua=obj.get("ua"))
            except ValueError as e:
                self._tra(400, {"ok": False, "msg": str(e)}, origin=o)
                return
            except Exception as e:                   # noqa: BLE001 - trả lỗi cho tiện ích
                self._tra(500, {"ok": False, "msg": "%s: %s" % (type(e).__name__, e)},
                          origin=o)
                return
            if callable(_Handler.on_log):
                _Handler.on_log("[cookie] nhận %d cookie cho tài khoản '%s' (%s)"
                                % (so, acc_id, obj.get("nguon") or "tay"))
            self._tra(200, {"ok": True,
                            "msg": "đã lưu %d cookie cho '%s'" % (so, acc_id),
                            "account": acc_id}, origin=o)

        def log_message(self, fmt, *args):    # tắt log mặc định ra stderr
            pass

    return _Handler


class _MayChu(ThreadingHTTPServer):
    """ThreadingHTTPServer nhưng KHÔNG cho cướp cổng của tiến trình khác.

    ``HTTPServer`` mặc định bật ``allow_reuse_address``. Trên Windows, cờ đó cho phép
    một tiến trình thứ hai bind ĐÈ lên cổng mà tiến trình khác đang nghe — bind vẫn
    "thành công", rồi kết nối tới rơi vào tiến trình nào là tuỳ hệ điều hành.

    ĐÃ DÍNH THẬT 25/08/2026: một cửa sổ app cũ đang nghe 8766, tiến trình thứ hai bind
    đè lên được, và cookie tiện ích gửi lên rơi vào bản CŨ — báo lỗi bằng câu của phiên
    bản cũ trong khi code trên đĩa đã sửa xong. Kiểu hỏng này gần như không thể lần ra
    vì mọi thứ nhìn riêng đều đúng.

    Tắt cờ đi thì tiến trình thứ hai ăn OSError ngay lúc bind, và giao diện đã có sẵn
    câu "Cổng %d đang bận — có thể cửa sổ CapCut TTS khác đang nghe rồi".
    """

    allow_reuse_address = False


class CookieServer:
    """Máy chủ nhận cookie chạy nền. Gọi start()/stop(); start 2 lần vẫn an toàn."""

    def __init__(self, kho, port=None, on_log=None):
        self.kho = kho
        # port=0 nghĩa là "xin hệ điều hành một cổng rảnh" (test dùng), KHÁC HẲN
        # port=None nghĩa là "dùng cổng mặc định của kho". `port or kho.port` gộp hai ý
        # đó làm một vì 0 là giá trị falsy -> test xin cổng rảnh lại đi bind đúng cổng
        # thật của app đang chạy.
        self.port = int(kho.port if port is None else port)
        self.on_log = on_log
        self._handler = tao_handler(kho)
        self._httpd = None
        self._thread = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return self.port
        self._handler.on_log = self.on_log
        self._httpd = _MayChu(("127.0.0.1", self.port), self._handler)
        # port=0 -> hệ điều hành vừa cấp cổng thật; ghi lại để bên gọi biết nghe ở đâu.
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever,
                                        kwargs={"poll_interval": 0.3},
                                        daemon=True, name=self.kho.ten_luong)
        self._thread.start()
        if callable(self.on_log):
            self.on_log("[cookie] đang nghe http://127.0.0.1:%d — mở tiện ích rồi bấm "
                        "'Gửi vào app'." % self.port)
        return self.port

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        self._thread = None


# --------------------------------------------------------------------------- #
#  CLI dùng chung cho cả hai kho
# --------------------------------------------------------------------------- #
def cli(kho, mo_ta, argv=None, dong=None):
    """dong(x) -> chuỗi mô tả 1 tài khoản; để None thì dùng khuôn chung.
    Bản Gemini truyền khuôn riêng vì nó còn in thêm trạng thái 1PSIDTS."""
    import argparse
    ap = argparse.ArgumentParser(description=mo_ta)
    ap.add_argument("--serve", action="store_true",
                    help="Chạy máy chủ nhận cookie (Ctrl+C để dừng).")
    ap.add_argument("--port", type=int, default=kho.port)
    ap.add_argument("--list", action="store_true", help="Liệt kê tài khoản đã lưu.")
    ap.add_argument("--import-file", default=None, help="Nạp JSON cookie từ file.")
    ap.add_argument("--label", default=None, help="Đặt tên tài khoản khi nạp.")
    ap.add_argument("--delete", default=None, help="Xoá 1 tài khoản theo id.")
    ap.add_argument("--where", action="store_true", help="In đường dẫn file kho.")
    a = ap.parse_args(argv)

    if a.where:
        print(kho.store_path())
    if a.import_file:
        with open(a.import_file, "r", encoding="utf-8") as f:
            acc, so = kho.import_json(f.read(), a.label)
        print("Đã lưu %d cookie cho '%s'." % (so, acc))
    if a.delete:
        print("Đã xoá." if kho.delete_account(a.delete) else "Không có tài khoản đó.")
    if a.list or not (a.serve or a.import_file or a.delete or a.where):
        accs = kho.list_accounts()
        if not accs:
            print("Kho rỗng (%s).\nHãy cài tiện ích %s/ rồi bấm 'Gửi vào app'."
                  % (kho.store_path(), kho.ten_tien_ich))
        for x in accs:
            print(dong(x) if callable(dong) else
                  ("· %-16s %2d cookie  mới cách đây %5.1f phút  (%s)"
                   % (x["id"], x["so_cookie"], x["tuoi_giay"] / 60.0, x["source"])))
    if a.serve:
        srv = CookieServer(kho, a.port, on_log=lambda s: print(s, flush=True))
        srv.start()
        print("Ctrl+C để dừng.", flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            srv.stop()
            print("Đã dừng.")
    return 0
