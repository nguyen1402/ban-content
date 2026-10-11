# -*- coding: utf-8 -*-
"""Kho COOKIE ChatGPT web + máy chủ nhỏ nhận cookie từ tiện ích Chrome.

Song sinh với ``gemini_cookie_store.py``, khác đúng bốn thứ (xem cookie_store_base.py):

    kho     : %LOCALAPPDATA%\\CapCutTTS\\chatgpt_cookies.json
    cookie  : ``__Secure-next-auth.session-token``  (HttpOnly -> chỉ tiện ích đọc được)
    cổng    : 8766  (Gemini giữ 8765, hai máy chủ chạy song song được)
    trang   : chatgpt.com

Vì sao là một kho RIÊNG chứ không nhét chung: hạn mức, tài khoản và cách hỏng của hai
dịch vụ không liên quan gì nhau. Gộp chung thì "xoay tài khoản" sẽ đẩy lô dịch sang một
tài khoản của dịch vụ khác — vô nghĩa. Tách kho cũng để cookie ChatGPT hỏng không kéo
theo đường Gemini đang chạy tốt.

BA CỘT MỐC CẦN NHỚ khi đọc log lỗi ở ``chatgpt_web_client.py``:
  * ``__Secure-next-auth.session-token`` — phiên đăng nhập. Thiếu = chưa đăng nhập.
  * ``cf_clearance`` — vé qua Cloudflare, GẮN VỚI (IP + User-Agent). Vì app chạy ngay
    trên máy có Chrome nên IP khớp; còn User-Agent thì tiện ích đẩy kèm và client phải
    dùng ĐÚNG chuỗi đó, sai một ký tự là Cloudflare chặn.
  * ``oai-did`` / ``__cf_bm`` — hai cookie phụ, thiếu vẫn chạy được nhưng có thì đỡ bị hỏi.
"""

import sys

from cookie_store_base import Kho, CookieServer as _CookieServer, cli, slug, store_dir

DEFAULT_PORT = 8766

# Cookie bắt buộc phải có thì phiên mới dùng được.
#
# ĐO 25/08/2026: trên chatgpt.com thật, cookie này thường KHÔNG tồn tại dưới tên trần mà
# bị NextAuth cắt thành ``…session-token.0`` + ``…session-token.1`` (token JWT vượt trần
# ~4096 byte của một cookie). Mọi phép xét "có đăng nhập chưa" phải đi qua
# ``gia_tri_phien()`` chứ đừng tra thẳng tên này — tra thẳng là từ chối oan tài khoản
# đang đăng nhập tử tế.
COOKIE_BAT_BUOC = "__Secure-next-auth.session-token"
# Tên cookie kết thúc bằng một UUID = cookie của MỘT cuộc trò chuyện (xem KHO bên dưới).
COOKIE_THEO_HOI_THOAI = (r"_[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                         r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

KHO = Kho(
    ten_file="chatgpt_cookies.json",
    env_path="CHATGPT_COOKIE_STORE",
    cookie_bat_buoc=COOKIE_BAT_BUOC,
    port=DEFAULT_PORT,
    trang_dang_nhap="chatgpt.com",
    co_cookie=(("co_session", COOKIE_BAT_BUOC),
               ("co_cf", "cf_clearance")),
    ten_luong="chatgpt-cookie-server",
    ten_tien_ich="gemini_cookie_ext",
    # Token phiên NextAuth đổi liên tục (app hâm nóng ghi token mới) -> nhãn tự sinh
    # không dựng lại được từ cookie hiện tại; xem Kho.nhan_tu_sinh (02/10/2026).
    phien_xoay=True,
    # Cookie THEO TỪNG CUỘC TRÒ CHUYỆN ('conv_key_<uuid>', 'history_off_<uuid>'): mỗi
    # lượt app hỏi ChatGPT để lại một cặp, kho từng giữ mãi. Đo 05/10/2026: acc4 tích
    # 138 cặp = 300 cookie ~27 KB mỗi request -> máy chủ trả 200 mà KHÔNG có phiên
    # ("không có accessToken"); chỉ gửi 6 cookie cần thiết thì có token ngay.
    bo_ten_cookie=COOKIE_THEO_HOI_THOAI,
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
    """Giá trị cookie phiên, đã ghép nếu bị chia mảnh `<tên>.0/.1/…`."""
    return KHO.gia_tri_phien(cookies)


def da_dang_nhap(cookies):
    return KHO.da_dang_nhap(cookies)


def la_ho_phien(ten):
    """Tên cookie thuộc họ cookie phiên (tên trần hoặc mảnh `.0/.1/…`)."""
    return KHO.la_ho_phien(ten)


def phien_bi_tron(cookies):
    """Bộ cookie có CẢ kiểu liền lẫn kiểu chia mảnh -> máy chủ nối thành rác."""
    return KHO.phien_bi_tron(cookies)


def thay_cookie(acc_id, cookies, source="app chữa phiên trộn"):
    """Thay nguyên bộ cookie của một bản ghi (không gộp)."""
    return KHO.thay_cookie(acc_id, cookies, source=source)


def bo_cookie_rac(cookies):
    """Bỏ cookie theo từng cuộc trò chuyện (conv_key_/history_off_<uuid>)."""
    return KHO.bo_cookie_rac(cookies)


def account_ids_from_store(accounts):
    """Sắp id theo độ mới từ một snapshot kho đã đọc sẵn."""
    return Kho.account_ids_from_store(accounts)


def account_ids():
    """Danh sách id tài khoản, tài khoản MỚI CẬP NHẬT đứng trước."""
    return KHO.account_ids()


def duplicate_account_groups(account_ids=None):
    """Nhóm các bản ghi có cùng cookie phiên, không làm lộ giá trị cookie."""
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
    """Máy chủ nhận cookie ChatGPT (cổng 8766)."""

    def __init__(self, port=DEFAULT_PORT, on_log=None):
        super().__init__(KHO, port=port, on_log=on_log)


def _dong(x):
    return ("· %-16s %2d cookie  cf_clearance:%s  mới cách đây %5.1f phút  (%s)"
            % (x["id"], x["so_cookie"], "có" if x["co_cf"] else "KHÔNG",
               x["tuoi_giay"] / 60.0, x["source"]))


def main(argv=None):
    return cli(KHO, "Kho cookie ChatGPT web (nhận từ tiện ích Chrome).",
               argv=argv, dong=_dong)


if __name__ == "__main__":
    sys.exit(main())
