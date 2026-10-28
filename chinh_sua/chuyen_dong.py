# -*- coding: utf-8 -*-
"""CHUYỂN ĐỘNG ẢNH TĨNH kiểu Ken Burns (28/10 user: "hiện tại tôi đang thấy nó đang phóng to ảnh, giờ có xóa logo rồi thì
không cần thiết, chỉ là cần thêm đa dạng di chuyển ảnh cho mượt mà hơn").

Công thức (tham khảo cách làm Ken Burns của Final Cut Pro / Premiere: chuyển động kiềm chế, có ease, đặt keyframe RA NGOÀI
điểm cắt để lúc chuyển cảnh ảnh vẫn đang trôi):
  * KHÔNG phóng nền 120% nữa (logo ✦ đã xoá): ảnh đẩy / kéo bắt đầu từ 100%; lia / nghiêng chỉ phóng VỪA ĐỦ chừa lề.
  * 8 kiểu: đẩy vào, kéo ra, lia trái, lia phải, nghiêng lên, nghiêng xuống, trôi chéo vào góc, kéo ra kèm trôi —
    không lặp kiểu của 2 ảnh ngay trước; có `huong` (trai/phai/len/xuong/vao/ra — điều phối ghi theo HÀNH ĐỘNG) thì theo.
  * Biên độ theo thời lượng: ~TOC_PHONG mỗi giây, kẹp [PHONG_MIN, PHONG_MAX] -> ảnh ngắn không giật, ảnh dài không trôi xa.
  * Mượt: pycapcut chỉ có keyframe TUYẾN TÍNH -> lấy mẫu đường smoothstep thành SO_KF keyframe; đường cong kéo dài ra
    ngoài hai đầu ảnh DEM giây nên lúc vào / ra ảnh đã đang trôi nhẹ (không khựng ở điểm cắt)."""

TOC_PHONG = 0.035      # phóng / trôi bao nhiêu (tỉ lệ khung) mỗi giây
PHONG_MIN = 0.06       # biên độ tối thiểu (ảnh ngắn)
PHONG_MAX = 0.14       # biên độ tối đa (ảnh dài)
DEM = 0.6              # giây đường cong kéo dài ra ngoài mỗi đầu ảnh
SO_KF = 8              # số keyframe mỗi thuộc tính
KIEU = ("vao", "ra", "trai", "phai", "len", "xuong", "cheo_vao", "cheo_ra")
_GAN = []              # kiểu của các ảnh vừa đặt (tránh lặp)


def _muot(t):
    return t * t * (3 - 2 * t)                               # smoothstep: chậm - nhanh - chậm


def _diem(d_us):
    """[(time_offset µs, tiến độ 0..1)] — tiến độ theo smoothstep trên khoảng [-DEM, d+DEM], chỉ lấy phần trong ảnh."""
    d = d_us / 1e6
    a, b = -DEM, d + DEM
    ra = []
    for k in range(SO_KF):
        t = d * k / (SO_KF - 1)
        u = _muot((t - a) / (b - a))
        u0, u1 = _muot((0 - a) / (b - a)), _muot((d - a) / (b - a))
        ra.append((min(int(t * 1e6), max(0, d_us - 1000)), (u - u0) / max(1e-6, u1 - u0)))
    return ra


def chon_kieu(k, huong=None):
    """Kiểu chuyển động cho ảnh thứ k: theo `huong` nếu có, không thì xoay vòng nhưng tránh 2 kiểu vừa dùng."""
    if huong in KIEU:                                        # 28/10: storyboard chọn cả kiểu trôi chéo theo nhịp
        kieu = huong
    else:
        kieu = next((KIEU[(k + j) % len(KIEU)] for j in range(len(KIEU)) if KIEU[(k + j) % len(KIEU)] not in _GAN[-2:]),
                    KIEU[k % len(KIEU)])
    _GAN.append(kieu)
    del _GAN[:-4]
    return kieu


def ken_burns(seg, d, k, KP, huong=None):
    """Gắn keyframe chuyển động cho đoạn ảnh `seg` dài d (µs), ảnh thứ k trong video -> tên kiểu đã dùng."""
    kieu = chon_kieu(k, huong)
    bien = min(PHONG_MAX, max(PHONG_MIN, TOC_PHONG * d / 1e6))
    goc = (k * 0.37) % 1.0                                   # góc trôi chéo đổi theo ảnh (không cùng một góc)
    huong_cheo = (1 if goc < 0.5 else -1, 1 if (goc * 2) % 1.0 < 0.5 else -1)
    if kieu in ("vao", "ra"):
        s0, s1 = (1.0, 1.0 + bien) if kieu == "vao" else (1.0 + bien, 1.0)
        x0 = x1 = y0 = y1 = 0.0
    elif kieu in ("trai", "phai", "len", "xuong"):
        lech = bien / 2                                      # trôi bao nhiêu thì phóng chừa lề bấy nhiêu (không lộ viền)
        s0 = s1 = 1.0 + bien
        dau = {"trai": 1, "phai": -1, "len": -1, "xuong": 1}[kieu]
        x0, x1 = (dau * lech, -dau * lech) if kieu in ("trai", "phai") else (0.0, 0.0)
        y0, y1 = (dau * lech, -dau * lech) if kieu in ("len", "xuong") else (0.0, 0.0)
    else:                                                    # trôi chéo: đẩy vào (hoặc kéo ra) + trôi về một góc
        lech = bien / 3
        s0, s1 = (1.0 + bien / 3, 1.0 + bien) if kieu == "cheo_vao" else (1.0 + bien, 1.0 + bien / 3)
        x0, y0 = 0.0, 0.0
        x1, y1 = huong_cheo[0] * lech, huong_cheo[1] * lech
        if kieu == "cheo_ra":
            x0, y0, x1, y1 = x1, y1, 0.0, 0.0
    for t, u in _diem(d):
        seg.add_keyframe(KP.uniform_scale, t, round(s0 + (s1 - s0) * u, 4))
        if x0 or x1:
            seg.add_keyframe(KP.position_x, t, round(x0 + (x1 - x0) * u, 4))
        if y0 or y1:
            seg.add_keyframe(KP.position_y, t, round(y0 + (y1 - y0) * u, 4))
    return kieu
