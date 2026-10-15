# Tiện ích lấy cookie Gemini / ChatGPT → Bán Content

> **Bản riêng của bán-content (14/10/2026).** Kho cookie RIÊNG `%LOCALAPPDATA%\BanContent\`, cổng **8785** (Gemini) / **8786** (ChatGPT) — độc lập hẳn với CapCut TTS Studio (kho `%LOCALAPPDATA%\CapCutTTS\`, cổng 8765/8766, tiện ích `capcut-tts-api\gemini_cookie_ext`). Bộ nhận tự bật khi mở giao diện bán-content (`mo_giao_dien.bat`); xem/dán/xoá tài khoản ở thẻ **🍪 Cookie** của giao diện. Phần hướng dẫn bên dưới chép từ bản CapCut — chỗ nào nói tab "Dịch SRT" thì hiểu là thẻ 🍪 Cookie.

Dùng để dịch SRT bằng **tài khoản web** (gemini.google.com hoặc chatgpt.com) thay cho
khoá API, nên không đụng trần RPM/RPD của API (lỗi 429) và ít gặp 503.

Một tiện ích phục vụ **hai dịch vụ**, mỗi bên một kho và một cổng riêng:

| Dịch vụ | Trang đăng nhập | Cookie phải có | Cổng app | File kho |
|---|---|---|---|---|
| Gemini | `gemini.google.com` | `__Secure-1PSID` | 8785 | `gemini_cookies.json` |
| ChatGPT | `chatgpt.com` | `__Secure-next-auth.session-token` *(thường ở dạng `.0`/`.1`)* | 8786 | `chatgpt_cookies.json` |

**Cookie phiên ChatGPT hay bị chia mảnh.** Đo 25/08/2026 trên Chrome thật: không hề có
cookie tên `__Secure-next-auth.session-token`, mà có `…session-token.0` và
`…session-token.1`. Đó là nết của NextAuth/Auth.js — token JWT vượt trần ~4096 byte của
**một** cookie thì nó cắt thành `<tên>.0`, `<tên>.1`, … Trình duyệt gửi đủ mảnh và máy
chủ tự ghép lại theo số thứ tự, nên app cũng **gửi nguyên các mảnh, không ghép trước**;
chỉ khi *xét* "đã đăng nhập chưa" và *dò bản ghi trùng* thì mới ghép để so.

Ô **Dịch vụ** ở đầu popup quyết định nhãn/cổng/nút bên dưới đang nói về bên nào. Hai kho
độc lập: cookie ChatGPT hỏng không đụng gì tới đường Gemini đang chạy.

## Vì sao phải là tiện ích?

Những cookie giữ phiên đăng nhập — `__Secure-1PSID`/`__Secure-1PSIDTS` của Gemini,
`__Secure-next-auth.session-token` và `cf_clearance` của ChatGPT — đều được đánh dấu
**HttpOnly**: mở DevTools chép bằng JavaScript không thấy, còn tiện ích có quyền `cookies`
thì đọc được. Cookie `__Secure-1PSIDTS` lại bị Google **xoay ~10 phút một lần**, nên tiện
ích tự đẩy lại bản mới mỗi khi cookie đổi, khỏi phải chép tay lại từng lúc.

### Riêng ChatGPT: `cf_clearance`

`cf_clearance` là vé qua Cloudflare và nó **gắn với cặp (IP + User-Agent)**. App chạy ngay
trên máy có Chrome nên IP khớp sẵn; còn User-Agent thì tiện ích đẩy kèm và app dùng đúng
chuỗi đó. Vì vậy:

* **Không có `cf_clearance` là bình thường** — Cloudflare chỉ cấp nó sau một lần thật sự
  bắt vượt kiểm tra. Popup chỉ nhắc bằng chữ xám, không tô đỏ.
* Nếu app báo bị Cloudflare chặn → mở lại `chatgpt.com` cho qua trang kiểm tra, rồi bấm
  **Gửi vào app** để lấy vé mới.
* Đổi mạng/VPN sau khi lấy cookie → vé hết hiệu lực, làm lại như trên.
* Nếu ChatGPT bắt vượt **Turnstile**, đường cookie không qua được (Python không chạy được
  JS của họ). App báo thẳng điều đó thay vì thử lại cho tốn lượt.

## Cài (Chrome / Edge / Cốc Cốc)

1. Mở `chrome://extensions` (Edge: `edge://extensions`).
2. Bật **Chế độ dành cho nhà phát triển** (Developer mode) — công tắc góc trên bên phải.
3. Bấm **Tải tiện ích đã giải nén** (Load unpacked) → chọn thư mục này:
   `D:\CapCutTTS\bán-content\cookie_ext`
4. Ghim biểu tượng tiện ích ra thanh công cụ cho dễ bấm.

## Dùng

1. Trong tab **Dịch SRT**, tích **Gemini web (cookie)** hoặc **ChatGPT web (cookie)** —
   hoặc bấm thẳng nút **🍪 Dịch bằng cookie Gemini** / **🤖 Dịch bằng cookie ChatGPT**.
   App tự bật bộ nhận đúng cổng của nguồn đó; không cần nhớ bấm **Nhận cookie**.
2. Mở `https://gemini.google.com/app` (hoặc `https://chatgpt.com/`) và **đăng nhập**.
3. Bấm biểu tượng tiện ích → chọn đúng **Dịch vụ** → thấy dòng “Đã đăng nhập — thấy N cookie”.
4. Đặt **Tên tài khoản** riêng, ví dụ `acc1`. Tên này phải khác tên của các tài khoản
   khác, nếu trùng thì bản gửi sau sẽ cập nhật đè đúng mục cùng tên. Tên của hai dịch vụ
   nằm ở hai kho khác nhau nên trùng tên giữa Gemini và ChatGPT không sao.
5. Chỉ ở lần thiết lập đầu tiên, bấm **Gửi vào app**. Thấy “Đã gửi — đã lưu N cookie”
   là xong.
6. Để nguyên ô **tự gửi lại**: tiện ích tự gửi khi cookie đổi và mỗi 5 phút, cho **cả
   hai** dịch vụ đang đăng nhập.

Sau lần gửi đầu, không phải tự lấy cookie cho từng phim. Chỉ cần Chrome/Profile đó đang
chạy và đã đăng nhập; app sẽ tự nghe khi nguồn cookie được chọn. Nút **Nhận cookie** vẫn
giữ lại để bật/tắt thủ công khi cần.

Muốn chạy bộ nhận không qua giao diện thì dùng:

```bash
python gemini_cookie_store.py --serve
```

```bash
python chatgpt_cookie_store.py --serve
```

Không bật được máy chủ nhận cookie? Bấm **Sao chép JSON** rồi dán vào ô nhận cookie
trong app, hoặc lưu ra file và chạy:

```bash
python gemini_cookie_store.py --import-file cookie.json --label acc1
```

Thử một tài khoản ChatGPT mà không cần mở giao diện (in ra đúng bước nào hỏng):

```bash
python chatgpt_web_client.py --check acc1
```

## “Chưa thấy cookie đăng nhập” dù đã đăng nhập rồi

Đây gần như luôn là **nền của tiện ích chưa được nạp lại**, không phải lỗi đăng nhập.
Chrome đọc lại `popup.html`/`popup.js` **mỗi lần bấm biểu tượng**, nhưng `background.js`
(service worker) thì **chỉ nạp lại khi bấm ⟳ Tải lại** ở `chrome://extensions`. Nên sau
khi cập nhật tiện ích, rất dễ thấy giao diện mới (đã có ô **Dịch vụ**) trong khi nền vẫn
là bản cũ — bản cũ không biết ô Dịch vụ nên luôn trả cookie Gemini.

Cách xử lý: `chrome://extensions` → bấm **⟳ Tải lại** trên thẻ tiện ích → mở lại popup.

Popup tự chẩn đoán và nói thẳng đang vướng cái nào:

| Popup báo | Nghĩa là | Làm gì |
|---|---|---|
| “Nền của tiện ích là **bản X**, popup cần **Y**” | service worker chưa nạp lại | bấm **⟳ Tải lại** |
| “Nền trả cookie của *gemini* chứ không phải *chatgpt*” | như trên | bấm **⟳ Tải lại** |
| “Không đọc được **cookie nào** của chatgpt.com” | thiếu quyền với miền mới | **Chi tiết** → **Quyền truy cập trang** → *Trên tất cả các trang* → **⟳ Tải lại** |
| “Đọc được N cookie … nhưng không có `…`” + danh sách tên | chưa đăng nhập thật, hoặc nhà cung cấp đã đổi tên cookie | gửi danh sách tên đó cho người bảo trì |

Popup so **số bản** của nền với số bản nó trông đợi, nên ca “quên Tải lại” bị bắt ngay cả
khi nền cũ vẫn tìm thấy cookie — lúc đó không có gì bên dưới đáng tin.

Danh sách đó chỉ là **tên** cookie, không có giá trị — chép ra ngoài được, không lộ phiên.

## Nhiều tài khoản

Mỗi hồ sơ Chrome (Profile) giữ một phiên đăng nhập riêng. Làm lần lượt:

1. Bấm ảnh đại diện góc phải Chrome → **Thêm hồ sơ**; tạo một Profile cho mỗi tài khoản.
2. Mở từng Profile → `chrome://extensions` → cài lại tiện ích bằng **Tải tiện ích đã
   giải nén**. Tiện ích của Profile này độc lập với Profile khác.
3. Trong Profile thứ nhất, đăng nhập tài khoản Google thứ nhất và mở Gemini.
4. Mở tiện ích, đặt tên `acc1`, để bật **tự gửi lại**, rồi bấm **Gửi vào app** một lần.
5. Lặp lại với Profile thứ hai/thứ ba nhưng dùng tài khoản Google khác và tên `acc2`,
   `acc3`.
6. Quay lại app: dòng trạng thái sẽ hiện tổng số **bản ghi** đã nhận. Nút
   **Kiểm tra tất cả / làm nóng** ép app gọi thử toàn bộ kho ngay (tối đa 6 tài khoản
   cùng lúc) và báo riêng số phiên **sống / lỗi / trùng cookie**.
7. Không bắt buộc bấm nút trước khi chạy. Cả **Dịch SRT** và **Tự động** đều tự tiền
   kiểm; riêng một loạt Tự động chỉ kiểm một lần rồi dùng cùng danh sách phiên sống
   cho các video sau. Kết quả được dùng lại tối đa 30 phút và mất hiệu lực ngay khi
   tiện ích đẩy cookie mới.
8. App chỉ giao việc cho phiên đã kiểm là sống, dùng tối đa một lượt đồng thời trên
   mỗi tài khoản và cho các tài khoản khác nhau chạy song song. Bản ghi trùng cookie
   không tạo thêm làn hay hạn mức.

Để cookie luôn mới trong lúc dịch dài, nên giữ các cửa sổ Profile mở hoặc thu nhỏ.
Nhiều Profile đăng nhập **cùng một tài khoản Google** không tạo thêm quota hay thêm một
làn thực sự; muốn tăng tốc phải là các tài khoản Google khác nhau.

## Cookie được cất ở đâu?

`%LOCALAPPDATA%\BanContent\gemini_cookies.json` và `…\chatgpt_cookies.json` — **ngoài**
thư mục dự án, nên không bao giờ lọt vào git. Xem/xoá:

```bash
python gemini_cookie_store.py --list
```

```bash
python chatgpt_cookie_store.py --list
```

Đây là cookie đăng nhập Google/OpenAI: coi như mật khẩu, đừng gửi file này cho ai. Muốn
cắt quyền thì đăng xuất trong trình duyệt (cookie cũ hết hiệu lực) rồi xoá tài khoản khỏi
kho bằng `--delete <id>`.

## Máy chủ nhận cookie có mở cửa cho web ngoài không?

Không. Nó chỉ nghe `127.0.0.1` (máy khác không với tới) và chỉ nhận request có
`Origin: chrome-extension://…` — trang web thường bị trả 403.
