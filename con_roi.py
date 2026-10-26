# -*- coding: utf-8 -*-
"""CON RỐI NHÂN VẬT VẼ BẰNG CODE kiểu MS Paint — 25/10 user: "nhân vật không thể để AI vẽ (AI vẽ hoàn hảo quá) mà phải tự
vẽ rồi nhét vào bối cảnh; phong cách kênh là tự vẽ MS Paint". Kênh Lạnh Vcl làm đúng vậy: cùng một hình nhân vật dán vào
nhiều nền, chỉ đổi tư thế / nét mặt.

  ve(nv, tu_the, bieu_cam, huong) -> ảnh RGBA trong suốt (toàn thân, cao CAO px)
  ve_mat(nv, bieu_cam, huong)     -> ảnh RGBA cận mặt (đầu + vai)
  nv = {"toc": kiểu tóc, "mau_toc", "mau_da", "ao": kiểu áo, "mau_ao", "quan": kiểu quần, "mau_quan", "mau_giay",
        "phu_kien", "mau_phu_kien", "than", "dau"}  (màu "#rrggbb")

Nét vẽ: viền đen dày KHÔNG khử răng cưa, hơi run tay (điểm rung nhẹ, cố định theo hạt giống nên con rối không "nhảy"),
màu phẳng, không đổ bóng; đầu to thân nhỏ, mặt trắng chỉ có chấm mắt + một nét miệng."""
import math
import random

from PIL import Image, ImageDraw

CAO = 900                    # chiều cao ảnh con rối toàn thân (px)
DEN = (24, 24, 24, 255)
NET = 7                      # độ dày viền
TU_THE = ("dung", "cui_dau", "khoanh_tay", "gio_tay", "di", "ngoi", "chong_nanh", "chi_tay", "om_mat")
BIEU_CAM = ("binh_thuong", "liec", "buon", "cuoi", "cuoi_meo", "soc", "gian", "nham_mat", "khoc")
TOC = ("ngan", "rua", "mai_dai", "buoc", "hoi", "dau_dinh", "xoan", "dai_xoa", "chai_mai", "tem", "duoi_ngua")
AO = ("phong", "ba_lo", "so_mi", "khoac", "vay_lien")
QUAN = ("dai", "dui", "vay")
PHU_KIEN = ("", "kinh", "no", "mu", "rau")
# 25/10 user: phong cách nhân vật lấy từ PHÂN TÍCH KÊNH (plugin) — dáng thân + cỡ đầu
THAN = ("que", "gon", "thuong")          # que = tay chân que mảnh (stick man), gon = thân nhỏ, thuong = cân đối hơn
DAU = ("to", "vua", "nho")
_CO_DAU = {"to": 1.15, "vua": 1.0, "nho": 0.82}
_CO_THAN = {"que": (0.62, 0.42), "gon": (1.0, 1.0), "thuong": (1.12, 1.15)}   # (độ rộng thân, độ dày tay chân)


def _mau(x, mac_dinh):
    x = str(x or mac_dinh).lstrip("#")
    try:
        return tuple(int(x[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    except ValueError:
        return _mau(mac_dinh, "ffffff")


class _But:
    """Bút run tay: mọi điểm rung nhẹ theo hạt giống cố định."""

    def __init__(self, d, hat):
        self.d, self.r = d, random.Random(hat)

    def _run(self, pts, a=2.2):
        return [(x + self.r.uniform(-a, a), y + self.r.uniform(-a, a)) for x, y in pts]

    def hinh(self, pts, mau, net=NET):
        pts = self._run(pts)
        self.d.polygon(pts, fill=mau)
        self.d.line(pts + [pts[0]], fill=DEN, width=net, joint="curve")

    def elip(self, cx, cy, rx, ry, mau, net=NET, n=44, tu=0, den=360):
        pts = [(cx + rx * math.cos(math.radians(tu + (den - tu) * i / n)), cy + ry * math.sin(math.radians(tu + (den - tu) * i / n)))
               for i in range(n + (0 if den - tu >= 360 else 1))]
        if den - tu >= 360:
            self.hinh(pts, mau, net)
        else:
            self.d.line(self._run(pts, 1.2), fill=DEN, width=net, joint="curve")

    def net(self, pts, net=NET, mau=DEN):
        self.d.line(self._run(pts, 1.4), fill=mau, width=net, joint="curve")

    def tay(self, a, b, c, mau, day=26):
        """Cánh tay / chân: đoạn a->b->c dày `day`, viền đen, màu áo / quần."""
        day = int(day)
        for p, q in ((a, b), (b, c)):
            self.d.line([p, q], fill=DEN, width=day + 2 * NET)
        for p in (a, b, c):
            self.d.ellipse([p[0] - day / 2 - NET, p[1] - day / 2 - NET, p[0] + day / 2 + NET, p[1] + day / 2 + NET], fill=DEN)
        for p, q in ((a, b), (b, c)):
            self.d.line([p, q], fill=mau, width=day)
        for p in (a, b, c):
            self.d.ellipse([p[0] - day / 2, p[1] - day / 2, p[0] + day / 2, p[1] + day / 2], fill=mau)


def _diem(goc, dai, tu):
    a = math.radians(goc)
    return (tu[0] + dai * math.sin(a), tu[1] + dai * math.cos(a))


# tư thế: (nghiêng thân độ, cúi đầu px, tay trái, tay phải, chân trái, chân phải)
# tay: (vai->khuỷu, khuỷu->bàn tay) góc tính từ phương thẳng đứng hướng xuống, DƯƠNG = HƯỚNG RA NGOÀI người (code tự lật
# cho tay trái), âm = vắt vào trong; chân: góc thật trên ảnh (dương = sang phải ảnh)
_TT = {
    "dung":       (0, 0, (8, 4), (8, 4), (-3, 0), (3, 0)),
    "cui_dau":    (14, 40, (4, 0), (4, 0), (-3, 0), (3, 0)),
    "khoanh_tay": (0, 0, (20, -100), (20, -100), (-3, 0), (3, 0)),
    "gio_tay":    (0, 0, (8, 4), (150, 170), (-3, 0), (3, 0)),
    "di":         (4, 0, (-20, -10), (25, 15), (20, 5), (-22, -30)),
    "ngoi":       (0, 0, (10, -40), (10, -40), (80, 0), (80, 0)),
    "chong_nanh": (0, 0, (55, -40), (55, -40), (-8, 0), (8, 0)),
    "chi_tay":    (0, 0, (8, 4), (95, 92), (-3, 0), (3, 0)),
    "om_mat":     (6, 25, (30, -160), (30, -160), (-3, 0), (3, 0)),
}


def _dau(b, cx, cy, R, nv, bieu_cam, huong):
    """Đầu to tròn hơi dẹt, mặt trắng, tóc theo kiểu; mắt chấm + một nét miệng."""
    da = _mau(nv.get("mau_da"), "fbfaf5")
    toc = _mau(nv.get("mau_toc"), "1e1e1e")
    kieu = nv.get("toc") if nv.get("toc") in TOC else "ngan"
    if kieu in ("mai_dai", "buoc"):                         # tóc dài sau gáy vẽ trước mặt
        b.hinh([(cx - R * 1.02, cy - R * 0.2), (cx - R * 1.1, cy + R * 1.25), (cx + R * 1.1, cy + R * 1.25), (cx + R * 1.02, cy - R * 0.2)], toc)
    elif kieu == "dai_xoa":                                  # dài xoã quá vai, hai bên lượn sóng
        b.hinh([(cx - R * 1.05, cy - R * 0.4), (cx - R * 1.25, cy + R * 0.6), (cx - R * 1.1, cy + R * 1.0), (cx - R * 1.3, cy + R * 1.6),
                (cx + R * 1.3, cy + R * 1.6), (cx + R * 1.1, cy + R * 1.0), (cx + R * 1.25, cy + R * 0.6), (cx + R * 1.05, cy - R * 0.4)], toc)
    elif kieu == "duoi_ngua":                                # đuôi ngựa vắt sau gáy sang một bên
        b.hinh([(cx + R * 0.7, cy - R * 0.7), (cx + R * 1.45, cy - R * 0.45), (cx + R * 1.55, cy + R * 0.5), (cx + R * 1.2, cy + R * 1.1),
                (cx + R * 1.05, cy + R * 0.3), (cx + R * 0.85, cy - R * 0.2)], toc)
    b.elip(cx, cy, R, R * 1.08, da)
    # tóc phía trên
    if kieu == "tem":                                        # đầu nấm: mũ tóc tròn, mái thẳng ngang lông mày
        b.hinh([(cx - R * 1.06, cy - R * 0.05)] + [(cx + R * 1.06 * math.cos(math.radians(a)), cy - R * 1.12 * math.sin(math.radians(a)))
                                                   for a in range(180, -1, -15)] + [(cx + R * 1.06, cy - R * 0.05), (cx - R * 1.06, cy - R * 0.05)], toc)
    elif kieu == "xoan":                                     # xoăn: chuỗi lọn tròn ôm đỉnh đầu
        for a in range(195, -16, -21):
            x, y = cx + R * 0.98 * math.cos(math.radians(a)), cy - R * 1.02 * math.sin(math.radians(a))
            b.elip(x, y, R * 0.26, R * 0.26, toc, net=5)
        b.elip(cx, cy - R * 0.8, R * 0.75, R * 0.35, toc, net=0)
    elif kieu in ("chai_mai", "dai_xoa", "duoi_ngua"):       # mũ tóc trơn + mái chéo một bên
        b.hinh([(cx - R * 1.04, cy - R * 0.1), (cx - R * 0.95, cy - R * 0.7), (cx - R * 0.5, cy - R * 1.08), (cx + R * 0.3, cy - R * 1.15),
                (cx + R * 0.9, cy - R * 0.85), (cx + R * 1.05, cy - R * 0.2), (cx + R * 0.75, cy - R * 0.45), (cx - R * 0.15, cy - R * 0.38),
                (cx - R * 0.75, cy - R * 0.15)], toc)
    elif kieu == "hoi":
        b.elip(cx, cy - R * 0.55, R * 0.95, R * 0.55, toc, tu=180, den=360)
        b.hinh([(cx - R * 0.95, cy - R * 0.5), (cx - R * 0.6, cy - R * 1.05), (cx + R * 0.6, cy - R * 1.05), (cx + R * 0.95, cy - R * 0.5),
                (cx + R * 0.5, cy - R * 0.62), (cx - R * 0.5, cy - R * 0.62)], toc)
    else:
        rang = 7 if kieu in ("rua", "dau_dinh") else 4
        tren = [(cx - R * 1.03, cy - R * 0.25)]
        for i in range(rang + 1):                          # mái lởm chởm
            x = cx - R + 2 * R * i / rang
            y = cy - R * (0.42 if i % 2 else 0.2) * (1.4 if kieu == "rua" else 1)
            tren.append((x, y))
        tren += [(cx + R * 1.03, cy - R * 0.25), (cx + R * 0.85, cy - R * 0.95), (cx, cy - R * 1.2), (cx - R * 0.85, cy - R * 0.95)]
        if kieu == "dau_dinh":
            tren = [(x, y - (R * 0.25 if i % 2 else 0)) for i, (x, y) in enumerate(tren)]
        b.hinh(tren, toc)
        if kieu == "buoc":
            b.elip(cx, cy - R * 1.25, R * 0.28, R * 0.22, toc)
    # mắt + miệng (dịch theo hướng nhìn)
    dx = R * 0.12 * (1 if huong == "phai" else -1 if huong == "trai" else 0)
    ey, ex = cy + R * 0.12, R * 0.36
    mr = max(4, R * 0.075)
    for s in (-1, 1):
        x = cx + s * ex + dx
        if bieu_cam in ("nham_mat", "khoc"):
            b.net([(x - mr * 1.6, ey), (x + mr * 1.6, ey + (mr if bieu_cam == "khoc" else 0))], net=5)
        elif bieu_cam == "soc":
            b.elip(x, ey, mr * 2.2, mr * 2.2, (255, 255, 255, 255), net=5)
            b.d.ellipse([x - mr * 0.8, ey - mr * 0.8, x + mr * 0.8, ey + mr * 0.8], fill=DEN)
        else:
            lech = mr * 0.9 if bieu_cam == "liec" else 0
            b.d.ellipse([x - mr + lech * (1 if huong != "trai" else -1), ey - mr, x + mr + lech * (1 if huong != "trai" else -1), ey + mr], fill=DEN)
            if bieu_cam in ("liec", "gian", "buon"):          # mí / mày
                nghieng = {"liec": 0, "gian": -s * mr * 1.4, "buon": s * mr * 1.4}[bieu_cam]
                b.net([(x - mr * 2, ey - mr * 1.6 - nghieng), (x + mr * 2, ey - mr * 1.6 + nghieng)], net=5)
    if bieu_cam == "khoc":
        for s in (-1, 1):
            b.net([(cx + s * ex + dx, ey + mr * 2), (cx + s * ex + dx, ey + mr * 6)], net=5, mau=(90, 160, 230, 255))
    my, mw = cy + R * 0.55, R * 0.22
    mx = cx + dx
    if bieu_cam == "soc":
        b.elip(mx, my, mw * 0.6, mw * 0.8, (120, 30, 30, 255), net=5)
    elif bieu_cam == "cuoi":
        b.elip(mx, my - mw * 0.3, mw, mw * 0.6, DEN, net=5, tu=10, den=170)
    elif bieu_cam == "cuoi_meo":
        b.net([(mx - mw, my), (mx, my + mw * 0.15), (mx + mw, my - mw * 0.45)], net=5)
    elif bieu_cam in ("buon", "khoc"):
        b.elip(mx, my + mw * 0.4, mw * 0.8, mw * 0.45, DEN, net=5, tu=190, den=350)
    elif bieu_cam == "gian":
        b.net([(mx - mw, my + mw * 0.2), (mx, my - mw * 0.1), (mx + mw, my + mw * 0.2)], net=5)
    else:
        b.net([(mx - mw * 0.7, my), (mx + mw * 0.7, my)], net=5)
    pk = nv.get("phu_kien") or ""
    mau_pk = _mau(nv.get("mau_phu_kien"), "e0457b")
    if pk == "kinh":
        for s_ in (-1, 1):
            b.elip(cx + s_ * ex + dx, ey, mr * 2.6, mr * 2.2, (255, 255, 255, 0), net=5)
        b.net([(cx - ex + dx + mr * 2.6, ey), (cx + ex + dx - mr * 2.6, ey)], net=5)
    elif pk == "no":                                         # nơ trên tóc
        nx, ny = cx - R * 0.55, cy - R * 0.95
        b.hinh([(nx, ny), (nx - R * 0.42, ny - R * 0.25), (nx - R * 0.42, ny + R * 0.25)], mau_pk, net=5)
        b.hinh([(nx, ny), (nx + R * 0.42, ny - R * 0.25), (nx + R * 0.42, ny + R * 0.25)], mau_pk, net=5)
        b.elip(nx, ny, R * 0.1, R * 0.1, mau_pk, net=5)
    elif pk == "mu":                                         # mũ lưỡi trai
        b.hinh([(cx - R * 1.02, cy - R * 0.35)] + [(cx + R * 1.02 * math.cos(math.radians(a)), cy - R * 0.35 - R * 0.85 * math.sin(math.radians(a)))
                                                   for a in range(180, -1, -15)], mau_pk)
        b.hinh([(cx - R * 0.2, cy - R * 0.38), (cx + R * 1.5, cy - R * 0.38), (cx + R * 1.4, cy - R * 0.2), (cx - R * 0.2, cy - R * 0.22)], mau_pk, net=5)
    elif pk == "rau":
        b.hinh([(mx - mw * 1.1, my - mw * 0.35), (mx + mw * 1.1, my - mw * 0.35), (mx + mw * 0.8, my - mw * 0.05), (mx - mw * 0.8, my - mw * 0.05)],
               _mau(nv.get("mau_toc"), "1e1e1e"), net=4)


def ve(nv, tu_the="dung", bieu_cam="binh_thuong", huong="giua", hat=None):
    """Con rối toàn thân, nền trong suốt, cao CAO px; chân chạm đáy ảnh.
    25/10 user: "chỉ ưng phần đầu, thân tay chân xấu quá — vẽ giống người que kênh Lạnh Vcl mà Gemini tạo": tỉ lệ theo mẫu
    Flow/Gemini (đầu ~35% chiều cao, cổ nhỏ, áo phông tay ngắn ~25%, tay MẢNH màu da + bàn tay nhỏ, quần ống đứng ~33%,
    giày đen dẹt)."""
    tu_the = tu_the if tu_the in _TT else "dung"
    W, H = int(CAO * 0.75), CAO
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    b = _But(ImageDraw.Draw(im), hat if hat is not None else hash((str(nv), tu_the, bieu_cam)) & 0xFFFF)
    ao, quan = _mau(nv.get("mau_ao"), "6f8ea8"), _mau(nv.get("mau_quan"), "1f2742")
    giay, da = _mau(nv.get("mau_giay"), "1a1a1a"), _mau(nv.get("mau_da"), "fbfaf5")
    kieu_ao = nv.get("ao") if nv.get("ao") in AO else "phong"
    kieu_quan = nv.get("quan") if nv.get("quan") in QUAN else "dai"
    nghieng, cui, tt, tp, ct, cp = _TT[tu_the]
    R = H * 0.172 * _CO_DAU.get(nv.get("dau"), 1.0)
    rong_k, day_k = _CO_THAN.get(nv.get("than"), (1.0, 1.0))
    cx = W / 2
    dat = H * 0.985                                          # mặt đất
    chan_tren, chan_duoi = H * 0.15, H * 0.145
    ngoi = tu_the == "ngoi"
    hong_y = dat - H * 0.03 - (chan_tren + chan_duoi if not ngoi else chan_duoi + H * 0.02)
    vai_y = hong_y - H * 0.235
    lech = math.tan(math.radians(nghieng)) * (hong_y - vai_y)
    vai = (cx + lech, vai_y)
    rv, rh = H * 0.088 * rong_k, H * 0.078 * rong_k          # nửa rộng vai / hông
    if ngoi:                                                 # ghế nhựa đỏ dưới mông (kiểu quán vỉa hè)
        ghe = _mau(nv.get("mau_ghe"), "d33a3a")
        b.hinh([(cx - rh * 1.5, hong_y - H * 0.005), (cx + rh * 1.5, hong_y - H * 0.005), (cx + rh * 1.5, hong_y + H * 0.03),
                (cx - rh * 1.5, hong_y + H * 0.03)], ghe, net=5)
        for s_ in (-1, 1):
            b.hinh([(cx + s_ * rh * 1.35, hong_y + H * 0.03), (cx + s_ * rh * 1.05, hong_y + H * 0.03),
                    (cx + s_ * rh * 1.25, dat), (cx + s_ * rh * 1.6, dat)], ghe, net=5)
    # --- chân (quần ống đứng / quần đùi + chân trần / váy + chân trần)
    ong = H * 0.062 * day_k
    for goc, dx in ((ct, -1), (cp, 1)):
        hong = (cx + dx * rh * 0.48, hong_y)
        if ngoi:                                             # ngồi: đùi gập về phía trước (nhìn chính diện thấy ngắn lại)
            goi = (hong[0] + dx * H * 0.01, hong[1] + H * 0.035)
            ban = (goi[0], goi[1] + chan_duoi)
        else:
            goi = _diem(goc[0], chan_tren, hong)
            ban = _diem(goc[1], chan_duoi, goi)
        if kieu_quan == "dai":
            b.tay(hong, goi, ban, quan, day=ong)
        else:
            b.tay(hong, goi, ban, da, day=H * 0.026 * day_k)   # chân trần mảnh
            if kieu_quan == "dui":
                giua = ((hong[0] + goi[0]) / 2, (hong[1] + goi[1]) / 2)
                b.tay(hong, giua, giua, quan, day=ong * 1.08)
        b.elip(ban[0] + dx * H * 0.016, ban[1] + H * 0.006, H * 0.042, H * 0.017, giay, net=5)
    if kieu_quan == "vay":                                   # váy: hình thang từ hông
        b.hinh([(cx - rh * 0.95, hong_y - H * 0.02), (cx + rh * 0.95, hong_y - H * 0.02),
                (cx + rh * 1.45, hong_y + H * 0.11), (cx - rh * 1.45, hong_y + H * 0.11)], quan)
    # --- cổ + thân áo
    b.hinh([(vai[0] - H * 0.014, vai[1] - H * 0.03), (vai[0] + H * 0.014, vai[1] - H * 0.03),
            (vai[0] + H * 0.014, vai[1] + H * 0.01), (vai[0] - H * 0.014, vai[1] + H * 0.01)], da, net=5)
    than = [(vai[0] - rv, vai[1] + H * 0.012), (vai[0] - rv * 0.6, vai[1] - H * 0.004), (vai[0] + rv * 0.6, vai[1] - H * 0.004),
            (vai[0] + rv, vai[1] + H * 0.012), (cx + rh, hong_y + H * 0.012), (cx - rh, hong_y + H * 0.012)]
    if kieu_ao == "ba_lo":
        than[1], than[2] = (vai[0] - rv * 0.45, vai[1] - H * 0.004), (vai[0] + rv * 0.45, vai[1] - H * 0.004)
    b.hinh(than, ao, net=6)
    if kieu_ao == "so_mi":                                   # cổ áo trắng + hàng cúc
        b.hinh([(vai[0] - H * 0.03, vai[1] - H * 0.006), (vai[0], vai[1] + H * 0.03), (vai[0] + H * 0.03, vai[1] - H * 0.006)],
               (255, 255, 255, 255), net=4)
        for i in range(3):
            y = vai[1] + H * (0.06 + 0.055 * i)
            b.d.ellipse([vai[0] - 4, y - 4, vai[0] + 4, y + 4], fill=DEN)
    elif kieu_ao == "khoac":                                 # áo khoác mở: khoá kéo giữa + mũ sau gáy
        b.net([(vai[0], vai[1] + H * 0.005), (cx, hong_y + H * 0.01)], net=4)
    elif kieu_ao == "vay_lien":                              # váy liền: thân áo kéo dài xuống thành váy
        b.hinh([(cx - rh, hong_y), (cx + rh, hong_y), (cx + rh * 1.5, hong_y + H * 0.12), (cx - rh * 1.5, hong_y + H * 0.12)], ao, net=6)
    # --- tay: mảnh màu da, tay áo ngắn (phông / ba lỗ không tay) hoặc dài (sơ mi, khoác)
    tay_tren, tay_duoi = H * 0.112, H * 0.105
    for goc, dx in ((tt, -1), (tp, 1)):
        g1, g2 = goc[0] * dx, goc[1] * dx                    # góc khai báo "ra ngoài" -> góc thật trên ảnh
        a = (vai[0] + dx * rv * 0.86, vai[1] + H * 0.026)
        k = _diem(g1, tay_tren, a)
        c = _diem(g2, tay_duoi, k)
        dai_tay = kieu_ao in ("so_mi", "khoac")
        b.tay(a, k, c, ao if dai_tay else da, day=(H * 0.038 if dai_tay else H * 0.026) * day_k)
        if kieu_ao in ("phong", "vay_lien"):                 # tay áo ngắn
            m = (a[0] + (k[0] - a[0]) * 0.42, a[1] + (k[1] - a[1]) * 0.42)
            b.tay(a, m, m, ao, day=H * 0.048 * day_k)
        b.elip(c[0], c[1] + H * 0.006, H * 0.019, H * 0.024, da, net=5)
    # --- đầu
    dau_c = (vai[0] + lech * 0.25 + (cui * 0.25 if huong == "phai" else -cui * 0.25 if huong == "trai" else 0),
             vai[1] - H * 0.02 - R * 1.0 + cui)
    _dau(b, dau_c[0], dau_c[1], R, nv, bieu_cam, huong)
    if tu_the == "om_mat":                                   # hai bàn tay che mặt vẽ đè lên đầu
        for s in (-1, 1):
            b.elip(dau_c[0] + s * R * 0.35, dau_c[1] + R * 0.25, H * 0.026, H * 0.034, da, net=5)
    if huong == "trai":
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im


def ve_mat(nv, bieu_cam="binh_thuong", huong="giua", hat=None):
    """Cận mặt: đầu + vai, cao CAO px (dán to giữa khung cho cảnh cận mặt)."""
    W, H = int(CAO * 1.1), CAO
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    b = _But(ImageDraw.Draw(im), hat if hat is not None else hash((str(nv), "mat", bieu_cam)) & 0xFFFF)
    ao = _mau(nv.get("mau_ao"), "5a7d9a")
    b.hinh([(W * 0.12, H * 1.02), (W * 0.2, H * 0.8), (W * 0.8, H * 0.8), (W * 0.88, H * 1.02)], ao, net=10)
    _dau(b, W / 2, H * 0.43, H * 0.36, nv, bieu_cam, huong)
    return im


def dan(nen, roi, x_ty_le, cao_ty_le, day_ty_le=0.92):
    """Dán con rối lên nền: tâm ngang ở x_ty_le chiều rộng, cao = cao_ty_le chiều cao nền, chân ở day_ty_le chiều cao."""
    W, H = nen.size
    h = int(H * cao_ty_le)
    w = int(roi.width * h / roi.height)
    r = roi.resize((w, h), Image.NEAREST)                     # NEAREST: giữ nét răng cưa kiểu MS Paint
    nen = nen.convert("RGBA")
    nen.alpha_composite(r, (int(W * x_ty_le - w / 2), int(H * day_ty_le - h)))
    return nen
