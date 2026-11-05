// 05/11 user ("không thể sửa chữ … hoặc sửa mấy cái hiệu ứng"): hiệu ứng vào / ra / chuyển động liên tục của MỘT lớp,
// tính thuần từ khung hình — dùng chung cho trình sửa lớp (xem trước, sua_lop_shim) và bản dựng thật (HieuUng trong
// thu_vien), nên xem trước khớp đúng video. Không import gì (shim và thu_vien đều nạp được, không vòng import).
//   h = {vao: ''|'mo'|'trai'|'phai'|'duoi'|'tren'|'phong'|'nay', ra: ''|'mo'|'trai'|'phai'|'nho', khung: số khung, lien: ''|'phong'|'lui'|'troi'}
const kep = (t) => Math.min(1, Math.max(0, t));
const ra3 = (t) => 1 - Math.pow(1 - kep(t), 3);                           // chậm dần
const nay = (t) => { const c = 1.70158, u = kep(t) - 1; return 1 + (c + 1) * u * u * u + c * u * u; };   // vượt rồi về

export const VAO = {mo: 'Mờ dần vào', trai: 'Trượt từ trái', phai: 'Trượt từ phải', duoi: 'Trượt từ dưới lên',
  tren: 'Trượt từ trên xuống', phong: 'Phóng to vào', nay: 'Bật nảy'};
export const RA = {mo: 'Mờ dần ra', trai: 'Trượt ra trái', phai: 'Trượt ra phải', nho: 'Thu nhỏ ra'};
export const LIEN = {phong: 'Phóng chậm', lui: 'Lùi chậm', troi: 'Trôi ngang'};

export const tinhHieuUng = (f, dur, h) => {
  h = h || {};
  const k = Math.max(2, Number(h.khung) || 12);
  let op = 1, x = 0, y = 0, s = 1;
  const a = f / k;                                                       // tiến độ vào (0 -> 1)
  switch (h.vao) {
    case 'mo': op *= ra3(a); break;
    case 'trai': x += -240 * (1 - ra3(a)); op *= ra3(a * 1.6); break;
    case 'phai': x += 240 * (1 - ra3(a)); op *= ra3(a * 1.6); break;
    case 'duoi': y += 160 * (1 - ra3(a)); op *= ra3(a * 1.6); break;
    case 'tren': y += -160 * (1 - ra3(a)); op *= ra3(a * 1.6); break;
    case 'phong': s *= 0.82 + 0.18 * ra3(a); op *= ra3(a * 1.6); break;
    case 'nay': s *= a >= 1 ? 1 : 0.6 + 0.4 * nay(a); op *= ra3(a * 2); break;
    default:
  }
  const b = (dur - 1 - f) / k;                                           // còn lại trước khi ra (1 -> 0)
  switch (h.ra) {
    case 'mo': op *= ra3(b); break;
    case 'trai': x += -240 * (1 - ra3(b)); op *= ra3(b * 1.6); break;
    case 'phai': x += 240 * (1 - ra3(b)); op *= ra3(b * 1.6); break;
    case 'nho': s *= 0.82 + 0.18 * ra3(b); op *= ra3(b * 1.6); break;
    default:
  }
  const t = dur > 1 ? kep(f / (dur - 1)) : 0;
  switch (h.lien) {
    case 'phong': s *= 1 + 0.08 * t; break;
    case 'lui': s *= 1.08 - 0.08 * t; break;
    case 'troi': x += -50 * t; break;
    default:
  }
  return {opacity: op, translate: `${x.toFixed(1)}px ${y.toFixed(1)}px`, scale: String(+s.toFixed(4))};
};

// Interactive.Div đặt tuyệt đối, CO THEO NỘI DUNG (thử lopxe câu 9: khung bọc tuyệt đối 100% làm lớp co về 0 -> chữ xuống
// dòng từng từ). Khung bọc nằm TRONG DÒNG (relative): lớp giữ nguyên cỡ, con đặt tuyệt đối vẫn đúng chỗ (góc lớp = góc khung
// bọc). Tâm phóng: 'goc' (lớp dời góc — chữ / thẻ nhỏ) = góc trên trái; 'day' (lớp ở góc 0,0 phủ khung) = tâm khung hình.
export const kieuBoc = (kieu) => ({position: 'relative', transformOrigin: kieu === 'goc' ? '0 0' : '960px 540px'});
export const kieuLop = (st) => {
  st = st || {};
  const doi = (Number(st.left) || 0) !== 0 || (Number(st.top) || 0) !== 0;
  return doi && st.width == null && st.height == null ? 'goc' : 'day';
};
