// Popup: hiện tình trạng cookie, cho gửi sang app hoặc chép JSON ra tay.
//
// 25/08/2026 — popup phục vụ HAI dịch vụ. Ô "Dịch vụ" quyết định mọi thứ bên dưới đọc
// và ghi vào đâu: nhãn, cổng, trạng thái, nút. Cố ý KHÔNG hiện cả hai cùng lúc — người
// dùng lấy cookie cho từng bên một, hai cột song song chỉ tổ bấm nhầm.
const $ = (id) => document.getElementById(id);

// Bản của background.js mà popup này trông đợi. Phải khớp với hằng BAN bên đó.
//
// Vì sao phải so: Chrome đọc lại popup TỪ ĐĨA mỗi lần mở, còn service worker thì chỉ nạp
// lại khi bấm ⟳ "Tải lại". Sửa code xong mà quên Tải lại là chạy giao diện mới trên nền
// cũ — triệu chứng thì trông y như lỗi đăng nhập, mất cả buổi mò. So bản là biết ngay.
const BAN_MONG_DOI = "1.2.0";

const DICH_VU = {
  gemini: {
    ten: "Gemini",
    mien: "gemini.google.com",
    mo: "https://gemini.google.com/app",
    batBuoc: "__Secure-1PSID",
    phu: ["__Secure-1PSIDTS"],
    port: 8785,
    khoaLabel: "label", khoaPort: "port", khoaLastPush: "lastPush",
  },
  chatgpt: {
    ten: "ChatGPT",
    mien: "chatgpt.com",
    mo: "https://chatgpt.com/",
    batBuoc: "__Secure-next-auth.session-token",
    // cf_clearance là vé qua Cloudflare — thiếu nó thì app gọi được vài lượt rồi bị
    // chặn, nên phải nói rõ ở ô trạng thái chứ không im lặng.
    phu: ["cf_clearance"],
    port: 8786,
    khoaLabel: "labelChatgpt", khoaPort: "portChatgpt", khoaLastPush: "lastPushChatgpt",
  },
};

function dvHienTai() {
  return DICH_VU[$("dichvu").value] || DICH_VU.gemini;
}

function tenDvHienTai() {
  return $("dichvu").value in DICH_VU ? $("dichvu").value : "gemini";
}

// Mở popup.html bằng cách nháy đúp file (file:///…) thì KHÔNG có chrome.runtime:
// mọi lệnh đọc cookie ném lỗi và popup đứng ở "Đang đọc cookie…" trông như treo.
// Bắt ngay từ đầu và nói thẳng phải làm gì, thay vì để người dùng đoán.
function laTienIch() {
  return typeof chrome !== "undefined" && chrome.runtime && !!chrome.runtime.id;
}

function baoMoSaiCach() {
  $("trangthai").innerHTML =
    '<b class="loi">Đang mở như một file thường, không phải tiện ích.</b><br>' +
    "Trang này chỉ chạy được khi đã cài tiện ích:<br>" +
    "1) mở <b>chrome://extensions</b><br>" +
    "2) bật <b>Chế độ dành cho nhà phát triển</b><br>" +
    "3) bấm <b>Tải tiện ích đã giải nén</b> → chọn thư mục <b>gemini_cookie_ext</b><br>" +
    "4) bấm biểu tượng tiện ích trên thanh công cụ (không mở file này nữa).";
  for (const id of ["btnDay", "btnChep", "btnMo"]) $(id).disabled = true;
}

function motLuc(ts) {
  if (!ts) return "";
  const s = Math.round((Date.now() - ts) / 1000);
  if (s < 60) return s + " giây trước";
  if (s < 3600) return Math.round(s / 60) + " phút trước";
  return Math.round(s / 3600) + " giờ trước";
}

async function veTrangThai() {
  if (!laTienIch()) { baoMoSaiCach(); return; }
  const d = dvHienTai();
  const mac = { autoPush: true };
  mac[d.khoaLabel] = "";
  mac[d.khoaPort] = d.port;
  mac[d.khoaLastPush] = null;
  const cfg = await chrome.storage.local.get(mac);
  $("label").value = cfg[d.khoaLabel] || "";
  $("port").value = cfg[d.khoaPort] || d.port;
  $("autoPush").checked = cfg.autoPush;
  $("btnMo").textContent = "Mở " + d.ten;

  const tra = await chrome.runtime.sendMessage({ cmd: "lay", dv: tenDvHienTai() });
  const cookies = tra && tra.cookies;
  // 'phien' do NỀN tính (đã ghép mảnh `<tên>.0/.1/…` — xem giaTriPhien trong
  // background.js). Không tự tra cookies[d.batBuoc] ở đây: chatgpt.com chia mảnh cookie
  // phiên nên tên trần KHÔNG tồn tại, tra thẳng là báo "chưa đăng nhập" oan.
  const co = !!(tra && tra.phien);
  const ten = cookies ? Object.keys(cookies) : [];
  const thieu = co ? d.phu.filter((k) => !cookies[k]) : [];

  // Nền lệch bản thì KHÔNG có gì bên dưới đáng tin — kể cả khi nó bảo "đã đăng nhập",
  // vì bản cũ có thể đang trả cookie của dịch vụ khác. Nên xét bản TRƯỚC mọi thứ khác.
  if (!tra || !tra.ban || tra.ban !== BAN_MONG_DOI) {
    $("trangthai").innerHTML =
      `<b class="loi">Nền của tiện ích là bản ${(tra && tra.ban) || "cũ"}, ` +
      `popup cần ${BAN_MONG_DOI}.</b><br>Mở <b>chrome://extensions</b> → bấm ` +
      "<b>⟳ Tải lại</b> ở thẻ tiện ích này, rồi mở lại popup.";
  } else if (co) {
    $("trangthai").innerHTML =
      `<b class="ok">Đã đăng nhập ${d.ten}</b> — thấy ${ten.length} cookie.` +
      // Cookie "nên có" mà thiếu thì chỉ NHẮC, không tô đỏ: ĐO 25/08/2026 trên một
      // phiên chatgpt.com đăng nhập bình thường thì KHÔNG hề có cf_clearance —
      // Cloudflare chỉ cấp nó sau một lần bắt vượt kiểm tra. Tô đỏ ca bình thường là
      // dạy người dùng bỏ qua cảnh báo, đúng lúc cần thì họ không nhìn nữa.
      (thieu.length
        ? `<br><span class="nho">Chưa có ${thieu.join(", ")} — bình thường; nếu app ` +
          "báo bị Cloudflare chặn thì mở lại trang cho qua kiểm tra rồi gửi lại cookie.</span>"
        : "");
  } else {
    // KHÔNG dừng ở câu "chưa thấy cookie" — câu đó đúng nhưng vô dụng, người dùng đã
    // đăng nhập rồi thì không biết phải làm gì tiếp. Nói luôn NỀN ĐANG ĐỌC ĐƯỢC GÌ:
    // ba dấu hiệu dưới đây phân biệt được ba nguyên nhân hoàn toàn khác nhau.
    // Tới đây thì nền chắc chắn đúng bản (đã xét ở trên), nên ba ca còn lại mới có nghĩa.
    let vi_sao;
    if (tra.dv !== tenDvHienTai()) {
      vi_sao = `Nền trả cookie của “${tra.dv}” chứ không phải “${tenDvHienTai()}”. ` +
               'Bấm <b>⟳ Tải lại</b> ở chrome://extensions.';
    } else if (!ten.length) {
      vi_sao = `Không đọc được <b>cookie nào</b> của ${d.mien}. Thường là tiện ích chưa ` +
               'có quyền với miền này: <b>chrome://extensions</b> → <b>Chi tiết</b> → ' +
               '<b>Quyền truy cập trang</b> → chọn <b>Trên tất cả các trang</b>, rồi ' +
               'bấm <b>⟳ Tải lại</b>.';
    } else {
      // Đọc được cookie của đúng miền nhưng KHÔNG có cookie phiên đang chờ (kể cả dạng
      // chia mảnh) -> hoặc chưa đăng nhập thật, hoặc nhà cung cấp đã đổi tên cookie.
      // Liệt kê TÊN (không phải giá trị) để biết ngay là ca nào.
      vi_sao = `Đọc được ${ten.length} cookie của ${d.mien} nhưng không có ` +
               `<code>${d.batBuoc}</code> (kể cả dạng chia mảnh <code>.0/.1</code>).` +
               `<br><span class="nho">Tên đang thấy: ` +
               `${ten.slice(0, 14).join(", ")}${ten.length > 14 ? ", …" : ""}</span>`;
    }
    $("trangthai").innerHTML =
      `<b class="loi">Chưa thấy cookie đăng nhập ${d.ten}.</b><br>${vi_sao}`;
  }

  const lp = cfg[d.khoaLastPush];
  $("ketqua").innerHTML = lp
    ? `Lần gửi gần nhất: <span class="${lp.ok ? "ok" : "loi"}">${lp.ok ? "OK" : "hỏng"}</span> — ${lp.msg} (${motLuc(lp.ts)})`
    : "";
}

async function luuCaiDat() {
  const d = dvHienTai();
  const obj = { autoPush: $("autoPush").checked };
  obj[d.khoaLabel] = $("label").value.trim();
  obj[d.khoaPort] = parseInt($("port").value, 10) || d.port;
  await chrome.storage.local.set(obj);
}

$("dichvu").addEventListener("change", () => {
  // KHÔNG lưu trước khi đổi: ô nhãn/cổng đang hiển thị giá trị của dịch vụ CŨ, lưu lúc
  // này là ghi đè cấu hình của dịch vụ MỚI bằng số của dịch vụ cũ.
  veTrangThai().catch((e) => {
    $("trangthai").innerHTML = '<b class="loi">Lỗi popup:</b> ' + ((e && e.message) || e);
  });
});

$("btnDay").addEventListener("click", async () => {
  await luuCaiDat();
  $("ketqua").textContent = "Đang gửi…";
  const kq = await chrome.runtime.sendMessage({ cmd: "day", dv: tenDvHienTai() });
  $("ketqua").innerHTML = `<span class="${kq.ok ? "ok" : "loi"}">${kq.ok ? "Đã gửi" : "Hỏng"}</span> — ${kq.msg}`;
});

$("btnChep").addEventListener("click", async () => {
  await luuCaiDat();
  const tra = await chrome.runtime.sendMessage({ cmd: "lay", dv: tenDvHienTai() });
  const cookies = tra.cookies;
  const label = $("label").value.trim() ||
    ("acc-" + (tra.phien || "trong").slice(-8).replace(/[^A-Za-z0-9]/g, ""));
  await navigator.clipboard.writeText(JSON.stringify({ label, cookies }, null, 1));
  $("ketqua").innerHTML = `<span class="ok">Đã chép JSON</span> — dán vào ô nhận cookie của app.`;
});

$("btnMo").addEventListener("click", () => {
  chrome.tabs.create({ url: dvHienTai().mo });
});

for (const id of ["label", "port", "autoPush"]) {
  $(id).addEventListener("change", () => { if (laTienIch()) luuCaiDat(); });
}
// Lỗi bất ngờ cũng phải HIỆN LÊN ô trạng thái: popup không có chỗ xem console tiện,
// im lặng là kiểu hỏng khó dò nhất.
veTrangThai().catch((e) => {
  $("trangthai").innerHTML = '<b class="loi">Lỗi popup:</b> ' + ((e && e.message) || e);
});
