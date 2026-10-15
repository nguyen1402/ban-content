# -*- coding: utf-8 -*-
"""Kho COOKIE Gemini web + máy chủ nhỏ nhận cookie từ tiện ích Chrome.

Vì sao có file này: dịch bằng *khoá API* Gemini luôn đụng trần RPM/RPD (429) và 503.
Còn tài khoản Gemini web (gemini.google.com) dùng hạn mức của NGƯỜI DÙNG, đếm theo
kiểu khác. Muốn gọi được web đó từ Python thì phải có cookie đăng nhập, mà hai cookie
quyết định (``__Secure-1PSID``, ``__Secure-1PSIDTS``) là HttpOnly — chỉ tiện ích trình
duyệt (thư mục ``gemini_cookie_ext/``) mới đọc được.

Đường đi: tiện ích  --POST /cookies-->  máy chủ này  -->  gemini_cookies.json
                                                     -->  gemini_web_client.py

Cookie ``__Secure-1PSIDTS`` bị Google xoay ~10 phút/lần, nên tiện ích tự đẩy lại mỗi
khi cookie đổi. File kho vì thế luôn có bản mới; client chỉ cần đọc lại khi thấy mốc
``updated`` đổi.

AN TOÀN: máy chủ chỉ nghe 127.0.0.1 (không ra mạng ngoài) và chỉ nhận POST có
``Origin: chrome-extension://…`` — trang web bình thường không đẩy rác vào được. File
kho nằm ở %LOCALAPPDATA%\\BanContent (NGOÀI repo) nên cookie không lọt vào git.

25/08/2026 — phần THÂN của kho đã dọn sang ``cookie_store_base.Kho`` để dùng chung
với kho cookie ChatGPT (``chatgpt_cookie_store.py``): hai bên chỉ khác tên file kho,
cookie bắt buộc, cổng nghe và trang phải đăng nhập. File này giữ NGUYÊN mọi tên hàm
và hành vi cũ — mọi nơi đang ``import gemini_cookie_store`` không phải sửa gì.
"""

import sys

from cookie_store_base import Kho, CookieServer as _CookieServer, cli, slug, store_dir

DEFAULT_PORT = 8785                                     # 14/10: CapCut TTS Studio giữ 8765

# Cookie bắt buộc phải có thì phiên mới dùng được.
COOKIE_BAT_BUOC = "__Secure-1PSID"

KHO = Kho(
    ten_file="gemini_cookies.json",
    env_path="BC_GEMINI_COOKIE_STORE",
    cookie_bat_buoc=COOKIE_BAT_BUOC,
    port=DEFAULT_PORT,
    trang_dang_nhap="gemini.google.com",
    co_cookie=(("co_1psid", "__Secure-1PSID"),
               ("co_1psidts", "__Secure-1PSIDTS")),
    ten_luong="gemini-cookie-server",
    ten_tien_ich="cookie_ext",
)


def store_path():
    return KHO.store_path()


def load_store():
    """Đọc kho; hỏng/chưa có -> kho rỗng (không ném lỗi ra ngoài)."""
    return KHO.load_store()


def save_account(label, cookies, source="extension", ua=None):
    """Ghi/cập nhật 1 tài khoản. Trả (account_id, số cookie đã lưu)."""
    return KHO.save_account(label, cookies, source=source, ua=ua)


def delete_account(acc_id):
    return KHO.delete_account(acc_id)


def get_account(acc_id):
    """Trả bản ghi tài khoản (có cookie) hoặc None."""
    return KHO.get_account(acc_id)


def gia_tri_phien(cookies):
    """Giá trị cookie phiên. Gemini không chia mảnh cookie nên đây chỉ là tra thẳng —
    giữ cùng tên hàm với kho ChatGPT để bên gọi không phải phân biệt hai kho."""
    return KHO.gia_tri_phien(cookies)


def da_dang_nhap(cookies):
    return KHO.da_dang_nhap(cookies)


def account_ids_from_store(accounts):
    """Sắp id theo độ mới từ một snapshot kho đã đọc sẵn."""
    return Kho.account_ids_from_store(accounts)


def account_ids():
    """Danh sách id tài khoản, tài khoản MỚI CẬP NHẬT đứng trước."""
    return KHO.account_ids()


def duplicate_account_groups(account_ids=None):
    """Nhóm các bản ghi có cùng cookie phiên chính, không làm lộ giá trị cookie."""
    return KHO.duplicate_account_groups(account_ids)


def unique_account_ids(ids=None):
    """Giữ một làn cho mỗi cookie phiên giống hệt nhau, ưu tiên id đứng trước."""
    return KHO.unique_account_ids(ids)


def list_accounts():
    """Danh sách tóm tắt để hiện lên giao diện — KHÔNG kèm giá trị cookie."""
    return KHO.list_accounts()

def named_account_ids(ids=None):
    """Chỉ tài khoản người dùng tự đặt tên; lọc ra rỗng thì trả lại nguyên danh sách."""
    return KHO.named_account_ids(ids)



def import_json(text, label=None):
    """Nhận JSON dán tay từ nút 'Sao chép JSON' của tiện ích (hoặc từ file)."""
    return KHO.import_json(text, label)


class CookieServer(_CookieServer):
    """Máy chủ nhận cookie Gemini. Chữ ký cũ CookieServer(port, on_log) giữ nguyên."""

    def __init__(self, port=DEFAULT_PORT, on_log=None):
        super().__init__(KHO, port=port, on_log=on_log)


def _dong(x):
    return ("· %-16s %2d cookie  1PSIDTS:%s  mới cách đây %5.1f phút  (%s)"
            % (x["id"], x["so_cookie"], "có" if x["co_1psidts"] else "KHÔNG",
               x["tuoi_giay"] / 60.0, x["source"]))


def main(argv=None):
    return cli(KHO, "Kho cookie Gemini web (nhận từ tiện ích Chrome).",
               argv=argv, dong=_dong)


if __name__ == "__main__":
    sys.exit(main())
