// Nền của tiện ích: gom cookie đăng nhập rồi đẩy về app (127.0.0.1).
//
// Vì sao cần TIỆN ÍCH mà không đọc bằng JavaScript trong trang: những cookie quyết định
// phiên đăng nhập ("__Secure-1PSID" của Gemini, "__Secure-next-auth.session-token" và
// "cf_clearance" của ChatGPT) đều là HttpOnly — trang web không đọc được. Chỉ quyền
// "cookies" của tiện ích mới thấy chúng.
//
// Cookie phiên bị nhà cung cấp XOAY liên tục (Gemini xoay "__Secure-1PSIDTS" khoảng 10
// phút/lần). Nên ngoài nút bấm tay còn có: nghe sự kiện cookie đổi + hẹn giờ định kỳ ->
// app luôn có bản mới nhất, người dùng không phải bấm lại mỗi lần hết hạn.
//
// 25/08/2026 — tiện ích nay phục vụ HAI dịch vụ. Mỗi dịch vụ một kho, một CỔNG riêng
// bên app (Gemini 8785, ChatGPT 8786) nên hai đường không giẫm lên nhau: cookie ChatGPT
// hỏng không đụng gì tới đường Gemini đang chạy.

const DICH_VU = {
  gemini: {
    ten: "Gemini",
    // getAll({url}) trả đúng những cookie SẼ ĐƯỢC GỬI tới địa chỉ này, kể cả HttpOnly —
    // không phải tự lọc theo tên nên nhà cung cấp có đổi tên cookie vẫn lấy đủ.
    url: "https://gemini.google.com/",
    mo: "https://gemini.google.com/app",
    batBuoc: "__Secure-1PSID",
    port: 8785,
    // Cookie tên khớp mẫu này + miền khớp thì coi là "phiên đổi" -> đẩy lại.
    tenCookie: /^(__Secure-[13]PSID(TS|CC)?|SID|SAPISID|NID)$/,
    mien: "google.com",
    khoaLabel: "label", khoaPort: "port", khoaLastPush: "lastPush",
  },
  chatgpt: {
    ten: "ChatGPT",
    url: "https://chatgpt.com/",
    mo: "https://chatgpt.com/",
    batBuoc: "__Secure-next-auth.session-token",
    port: 8786,
    tenCookie: /^(__Secure-next-auth\.session-token|cf_clearance|oai-did|oai-hlib|_puid|__cf_bm)$/,
    mien: "chatgpt.com",
    khoaLabel: "labelChatgpt", khoaPort: "portChatgpt", khoaLastPush: "lastPushChatgpt",
  },
};

// Bản của CHÍNH file này, trả về kèm mọi câu trả lời cho popup.
//
// Vì sao cần: popup.html/popup.js được Chrome đọc LẠI TỪ ĐĨA mỗi lần bấm biểu tượng,
// còn service worker này thì CHỈ nạp lại khi bấm ⟳ "Tải lại" ở chrome://extensions.
// Nên sau khi sửa code, hoàn toàn có thể thấy giao diện MỚI trong khi nền vẫn là bản CŨ:
// bản cũ không biết tham số 'dv' nên luôn trả cookie Gemini, và popup báo "chưa thấy
// cookie ChatGPT" dù đã đăng nhập. Popup so số bản này để nói thẳng ra điều đó thay vì
// để người dùng ngồi đoán.
const BAN = "1.2.0";

const ALARM = "day-cookie";
const DEBOUNCE_MS = 3000;

const debounceTimer = {};        // theo từng dịch vụ, không dùng chung một biến

function dv(ten) {
  return DICH_VU[ten] || DICH_VU.gemini;
}

// Giá trị cookie phiên, tự ghép nếu bị CHIA MẢNH.
//
// ĐO 25/08/2026 trên chatgpt.com thật: không hề có cookie tên
// "__Secure-next-auth.session-token", mà có "…session-token.0" và "…session-token.1".
// Đó là nết của NextAuth/Auth.js — token JWT vượt trần ~4096 byte của MỘT cookie thì nó
// cắt thành <tên>.0, <tên>.1, … Trình duyệt gửi đủ mảnh, máy chủ tự ghép theo số thứ tự.
// Vì vậy: xét "đã đăng nhập chưa" phải qua hàm này, còn lúc GỬI thì cứ gửi nguyên các
// mảnh, không ghép.
function giaTriPhien(cookies, ten) {
  const ck = cookies || {};
  if (ck[ten]) return ck[ten];
  const tienTo = ten + ".";
  const manh = Object.keys(ck)
    .filter((k) => k.startsWith(tienTo) && /^\d+$/.test(k.slice(tienTo.length)))
    // Sắp theo SỐ, không theo chữ: mảnh 10 phải đứng sau mảnh 9.
    .sort((a, b) => Number(a.slice(tienTo.length)) - Number(b.slice(tienTo.length)));
  return manh.map((k) => ck[k]).join("");
}

async function layCookie(tenDv) {
  const d = dv(tenDv);
  const list = await chrome.cookies.getAll({ url: d.url });
  const out = {};
  for (const c of list) out[c.name] = c.value;
  return out;
}

async function layCaiDat(tenDv) {
  const d = dv(tenDv);
  const mac = { autoPush: true };
  mac[d.khoaLabel] = "";
  mac[d.khoaPort] = d.port;
  mac[d.khoaLastPush] = null;
  const got = await chrome.storage.local.get(mac);
  return {
    label: got[d.khoaLabel] || "",
    port: got[d.khoaPort] || d.port,
    autoPush: got.autoPush,
    lastPush: got[d.khoaLastPush],
  };
}

function nhan(cookies, tenDv) {
  // Nhãn mặc định: 8 ký tự cuối của cookie phiên -> mỗi hồ sơ Chrome/tài khoản một nhãn.
  const sid = giaTriPhien(cookies, dv(tenDv).batBuoc);
  return sid ? "acc-" + sid.slice(-8).replace(/[^A-Za-z0-9]/g, "") : "acc-trong";
}

async function day(nguon, tenDv) {
  const d = dv(tenDv);
  const cfg = await layCaiDat(tenDv);
  const cookies = await layCookie(tenDv);
  if (!giaTriPhien(cookies, d.batBuoc)) {
    const kq = { ok: false, ts: Date.now(),
                 msg: `Chưa thấy cookie đăng nhập ${d.ten} — hãy mở ${d.url} và đăng nhập.` };
    await ghiKetQua(kq, tenDv);
    return kq;
  }
  const label = (cfg.label || "").trim() || nhan(cookies, tenDv);
  const url = `http://127.0.0.1:${cfg.port || d.port}/cookies`;
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        label,
        cookies,
        ua: navigator.userAgent,
        ts: Date.now(),
        nguon,
        dichvu: tenDv,
      }),
    });
    const txt = await r.text();
    let msg = txt;
    try { msg = JSON.parse(txt).msg || txt; } catch (e) { /* giữ nguyên văn bản */ }
    const kq = { ok: r.ok, ts: Date.now(), msg: r.ok ? msg : `HTTP ${r.status}: ${txt.slice(0, 120)}`, label, n: Object.keys(cookies).length };
    await ghiKetQua(kq, tenDv);
    return kq;
  } catch (e) {
    const kq = { ok: false, ts: Date.now(), msg: "Không nối được app (" + url + "). App đã bật 'Nhận cookie' chưa?", label };
    await ghiKetQua(kq, tenDv);
    return kq;
  }
}

async function ghiKetQua(kq, tenDv) {
  const obj = {};
  obj[dv(tenDv).khoaLastPush] = kq;
  await chrome.storage.local.set(obj);
  chrome.action.setBadgeText({ text: kq.ok ? "OK" : "!" });
  chrome.action.setBadgeBackgroundColor({ color: kq.ok ? "#1a7f37" : "#c62828" });
}

// Cookie đổi (đăng nhập lại, nhà cung cấp xoay cookie phiên…) -> đẩy lại, có chống dội.
chrome.cookies.onChanged.addListener((info) => {
  const ten = info.cookie && info.cookie.name;
  const dom = (info.cookie && info.cookie.domain) || "";
  if (!ten) return;
  for (const tenDv of Object.keys(DICH_VU)) {
    const d = DICH_VU[tenDv];
    if (!d.tenCookie.test(ten) || !dom.includes(d.mien)) continue;
    if (debounceTimer[tenDv]) clearTimeout(debounceTimer[tenDv]);
    debounceTimer[tenDv] = setTimeout(async () => {
      const cfg = await layCaiDat(tenDv);
      if (cfg.autoPush) day("cookie-doi", tenDv);
    }, DEBOUNCE_MS);
    return;
  }
});

chrome.alarms.create(ALARM, { periodInMinutes: 5 });
chrome.alarms.onAlarm.addListener(async (a) => {
  if (a.name !== ALARM) return;
  // Đẩy cho MỌI dịch vụ đang đăng nhập. Dịch vụ chưa đăng nhập thì day() tự bỏ qua,
  // không gửi rác và không làm hỏng trạng thái của dịch vụ kia.
  for (const tenDv of Object.keys(DICH_VU)) {
    const cfg = await layCaiDat(tenDv);
    if (!cfg.autoPush) continue;
    const cookies = await layCookie(tenDv);
    if (giaTriPhien(cookies, DICH_VU[tenDv].batBuoc)) day("hen-gio", tenDv);
  }
});

// Popup gọi vào đây (service worker giữ quyền cookies, popup thì đóng lúc nào không biết).
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    const tenDv = msg.dv || "gemini";
    if (msg.cmd === "day") sendResponse(Object.assign({ ban: BAN }, await day("tay", tenDv)));
    else if (msg.cmd === "lay") {
      // Trả kèm 'ban' và 'dv' đã hiểu: popup dựa vào đó để biết nền có đúng bản không,
      // và có nhận đúng dịch vụ đang chọn không. 'phien' tính LUÔN ở đây (đã ghép mảnh)
      // để popup khỏi phải chép lại logic ghép — hai file này không import nhau được.
      const ck = await layCookie(tenDv);
      sendResponse({ ban: BAN, dv: tenDv, cookies: ck,
                     phien: giaTriPhien(ck, dv(tenDv).batBuoc) });
    } else sendResponse({ ban: BAN, ok: false, msg: "Lệnh lạ" });
  })();
  return true;                      // giữ kênh mở cho trả lời bất đồng bộ
});
