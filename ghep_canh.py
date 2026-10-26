# -*- coding: utf-8 -*-
"""GHÉP CẢNH KIỂU CON RỐI — 25/10 user: nhân vật không để AI vẽ mỗi cảnh (ra "hoàn hảo quá", lệch kiểu MS Paint của kênh)
mà dán CÙNG MỘT nhân vật đã duyệt vào nền, như kênh Lạnh Vcl làm.

  Nền: ảnh bối cảnh (asset BC, không người) — kênh dùng lại cùng căn phòng nhiều lần.
  Nhân vật: biến thể ĐÃ DUYỆT trong kho_nhan_vat (Flow vẽ từ phôi code) hoặc con rối code (con_roi) cho vai phụ.
  Khung: rộng (người nhỏ, thấy chân), trung (người to, cắt ngang đùi), cận mặt (một người, đầu to, nền mờ)."""
import os

from PIL import Image, ImageFilter

# tư thế kho -> (tư thế, biểu cảm) của con rối code (vai phụ không có kho / tư thế chưa duyệt)
MAP_CODE = {
    "dung_binh_thuong": ("dung", "binh_thuong"), "dung_liec": ("dung", "liec"), "cui_dau_buon": ("cui_dau", "buon"),
    "cuoi": ("gio_tay", "cuoi"), "cuoi_meo": ("dung", "cuoi_meo"), "soc": ("dung", "soc"),
    "gian_chi_tay": ("chi_tay", "gian"), "khoanh_tay": ("khoanh_tay", "liec"), "om_mat_khoc": ("om_mat", "khoc"),
    "om_dau": ("om_mat", "buon"), "nhun_vai": ("dung", "cuoi_meo"), "cui_chao": ("cui_dau", "cuoi"),
    "dua_do": ("chi_tay", "buon"), "cam_dien_thoai": ("dung", "binh_thuong"), "ngoi_buon": ("ngoi", "buon"),
    "di_bo": ("di", "binh_thuong"), "chay": ("di", "soc"), "quay_lung": ("dung", "binh_thuong"),
}
# khung -> (chiều cao người / chiều cao ảnh, vị trí chân / chiều cao ảnh)
# 25/10 (thử 20 câu): "trung" cũ (1.2, 1.55) cắt ngang ngực -> mất hết cử chỉ (cúi đầu / ngồi / cúi chào chỉ còn cái đầu);
# con rối diễn bằng CẢ THÂN nên khung trung chỉ cắt ở bắp chân
CO = {"rong": (0.56, 0.95), "trung": (0.86, 1.04), "can_mat": (2.5, 2.42)}


def sprite(nv_asset, tu_the, so=0):
    """Ảnh RGBA của nhân vật ở tư thế: biến thể kho đã duyệt -> tư thế gần nhất đã duyệt -> con rối code."""
    import kho_nhan_vat
    nid = nv_asset.get("kho")
    if nid:
        f = kho_nhan_vat.chon(nid, tu_the, so) or kho_nhan_vat.chon(nid, "dung_binh_thuong", so)
        if not f:
            da = kho_nhan_vat.tu_the_da_duyet(nid)
            f = kho_nhan_vat.chon(nid, next(iter(da)), so) if da else None
        if f:
            return Image.open(f).convert("RGBA")
    import con_roi
    hinh = nv_asset.get("hinh") or {}
    if nid and not hinh:
        try:
            hinh = kho_nhan_vat.doc(nid).get("hinh") or {}
        except ValueError:
            hinh = {}
    t, b = MAP_CODE.get(tu_the, ("dung", "binh_thuong"))
    im = con_roi.ve(hinh, t, b)
    return im.crop(im.getbbox()) if im.getbbox() else im


def _huong(im):
    """+1 nếu khối hình lệch sang phải (tay chỉ / bước đi hướng phải), -1 nếu lệch trái, 0 nếu cân."""
    a = im.getchannel("A").resize((64, 64))
    px = a.load()
    tong = cot = 0
    for x in range(64):
        for y in range(64):
            if px[x, y] > 128:
                tong += 1
                cot += x
    if not tong:
        return 0
    lech = cot / tong / 63 - 0.5
    return 1 if lech > 0.04 else -1 if lech < -0.04 else 0


def ghep(nen_path, dat, khung, kich_thuoc, ra, so=0):
    """dat: [(nv_asset, tu_the, x 0..1)]. Ghép lên nền, lưu PNG `ra` -> ra."""
    W, H = kich_thuoc
    nen = Image.open(nen_path).convert("RGB")
    nen = _phu_kin(nen, W, H)
    if khung == "can_mat":
        w, h = nen.size                                        # nền cận: phóng vùng giữa + làm mờ cho nổi mặt
        nen = nen.crop((int(w * 0.18), int(h * 0.12), int(w * 0.82), int(h * 0.88))).resize((W, H)).filter(ImageFilter.GaussianBlur(6))
        dat = dat[:1]
    nen = nen.convert("RGBA")
    cao, chan = CO.get(khung, CO["rong"])
    if khung == "trung" and len(dat) >= 3:
        cao, chan = 0.72, 1.0
    for i, (nv, tu_the, x) in enumerate(dat):
        im = sprite(nv, tu_the, so + i)
        if im.getbbox():
            im = im.crop(im.getbbox())
        h = int(H * cao)
        w = int(im.width * h / im.height)
        if khung == "can_mat" and w > W * 0.9:
            w, h = int(W * 0.9), int(im.height * W * 0.9 / im.width)
        im = im.resize((w, h), Image.LANCZOS)
        muon = 1 if x < 0.5 else -1                           # quay về phía giữa khung (về phía người kia)
        if len(dat) > 1 and _huong(im) == -muon:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        nen.alpha_composite(im, (int(W * x - w / 2), int(H * chan - h)))
    nen.convert("RGB").save(ra)
    return ra


def _phu_kin(im, W, H):
    """Cắt + co ảnh cho phủ kín khung W x H (giữ tỉ lệ)."""
    r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r + 0.5), int(im.height * r + 0.5)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def vi_tri(n):
    """Vị trí ngang mặc định cho n người."""
    return {1: [0.5], 2: [0.32, 0.68], 3: [0.22, 0.5, 0.78]}.get(n, [0.12 + 0.76 * i / max(1, n - 1) for i in range(n)])


def anh_nhan_vat_code(nv_asset, ra):
    """Ảnh asset cho vai phụ con rối code (để giao diện storyboard hiện)."""
    import con_roi
    nen = Image.new("RGBA", (1200, 1200), (255, 255, 255, 255))
    r = con_roi.ve(nv_asset.get("hinh") or {}, "dung", "binh_thuong")
    nen.alpha_composite(r, ((1200 - r.width) // 2, 1200 - r.height - 60))
    os.makedirs(os.path.dirname(ra), exist_ok=True)
    nen.convert("RGB").save(ra)
    return ra
