"""29/10 user ("không được ghi đè phần tôi đã dựng, tôi mới chỉnh đến phút thứ 4"): ghép phần SAU một mốc giây của bản
nháp mới (✨ dựng lại theo kế hoạch đã lọc) vào BẢN SAO bản nháp người dùng đang sửa tay -> bản nháp thứ ba, tên mới.
Bản nháp của người dùng không bị đụng tới.

30/10: mở rộng thêm hàm ghep_khoang theo danh sách khoảng [[a1, b1], [a2, b2], ...] cho Bàn dựng theo câu:
Chỉ thay thế những câu người dùng đã chọn trong bàn dựng, các phần khác giữ nguyên 100% của bản gốc.
"""
import argparse
import copy
import glob
import json
import os
import shutil
import uuid

US = 1_000_000


def _doc(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _ghi(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def _vat_lieu(d):
    """id -> (tên danh sách trong materials, vật liệu)."""
    ra = {}
    for k, v in (d.get("materials") or {}).items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and m.get("id"):
                    ra[m["id"]] = (k, m)
    return ra


def _track(d, ten):
    return next((t for t in d.get("tracks", []) if t.get("name") == ten), None)


def ghep(goc, moi, moc_giay, track="hinh"):
    """goc, moi: nội dung draft_content.json -> nội dung mới (goc không bị sửa)."""
    ra = copy.deepcopy(goc)
    moc = int(round(moc_giay * US))
    t_ra, t_moi = _track(ra, track), _track(moi, track)
    if not t_ra or not t_moi:
        return ra, 0
    giu = []
    for s in t_ra["segments"]:
        a, dai = s["target_timerange"]["start"], s["target_timerange"]["duration"]
        if a >= moc:
            continue
        if a + dai > moc:                                    # vắt qua mốc -> cắt ngắn tới mốc
            cat = moc - a
            s["target_timerange"]["duration"] = cat
            if s.get("source_timerange"):
                toc = float(s.get("speed") or 1.0)
                s["source_timerange"]["duration"] = int(round(cat * toc))
        giu.append(s)
    vl_moi, vl_ra = _vat_lieu(moi), _vat_lieu(ra)
    them = 0
    for s in t_moi["segments"]:
        if s["target_timerange"]["start"] < moc:
            continue
        s = copy.deepcopy(s)
        for mid in [s.get("material_id")] + list(s.get("extra_material_refs") or []):
            if mid in vl_ra or mid not in vl_moi:
                continue
            k, m = vl_moi[mid]
            ra["materials"].setdefault(k, []).append(copy.deepcopy(m))
            vl_ra[mid] = (k, m)
        giu.append(s)
        them += 1
    t_ra["segments"] = sorted(giu, key=lambda x: x["target_timerange"]["start"])
    het = max((s["target_timerange"]["start"] + s["target_timerange"]["duration"] for t in ra["tracks"]
               for s in t["segments"]), default=0)
    ra["duration"] = max(int(ra.get("duration") or 0), het)
    return ra, them


def ghep_khoang(goc, moi, danh_sach_khoang, track="hinh"):
    """30/10 user: Ghép theo danh sách khoảng [[a1, b1], [a2, b2], ...] (giây).
    Trong bản gốc: track 'hinh' bỏ các đoạn nằm trong các khoảng (cắt mép nếu vắt qua).
    Trong bản mới: lấy các đoạn nằm trong các khoảng chép sang cùng mọi materials tham chiếu.
    Các track khác của bản gốc (âm thanh, nhạc, chữ...) giữ nguyên 100%."""
    ra = copy.deepcopy(goc)
    t_ra, t_moi = _track(ra, track), _track(moi, track)
    if not t_ra or not t_moi or not danh_sach_khoang:
        return ra, 0

    # Chuyển đổi khoảng sang microsecond
    khoang_us = []
    for k in danh_sach_khoang:
        t0, t1 = float(k[0]), float(k[1])
        if t1 > t0:
            khoang_us.append((int(round(t0 * US)), int(round(t1 * US))))
    khoang_us.sort()

    def _trung_khoang(s_start, s_end):
        for k0, k1 in khoang_us:
            if max(s_start, k0) < min(s_end, k1):
                return True
        return False

    giu = []
    # 1. Lọc và cắt các segment của bản gốc ngoài các khoảng
    for s in t_ra["segments"]:
        a = s["target_timerange"]["start"]
        b = a + s["target_timerange"]["duration"]
        # Phân đoạn s thành các mẩu nằm HOÀN TOÀN ngoài các khoảng
        muchs = [(a, b, s.get("source_timerange", {}).get("start", 0))]
        for k0, k1 in khoang_us:
            next_muchs = []
            for seg_a, seg_b, src_a in muchs:
                if seg_b <= k0 or seg_a >= k1:
                    next_muchs.append((seg_a, seg_b, src_a))
                else:
                    toc = float(s.get("speed") or 1.0)
                    if seg_a < k0:
                        next_muchs.append((seg_a, k0, src_a))
                    if seg_b > k1:
                        cut_left = k1 - seg_a
                        src_new = int(round(src_a + cut_left * toc))
                        next_muchs.append((k1, seg_b, src_new))
            muchs = next_muchs

        for seg_a, seg_b, src_a in muchs:
            dur = seg_b - seg_a
            if dur > 1000:
                s_new = copy.deepcopy(s)
                s_new["target_timerange"]["start"] = seg_a
                s_new["target_timerange"]["duration"] = dur
                if s_new.get("source_timerange"):
                    toc = float(s_new.get("speed") or 1.0)
                    s_new["source_timerange"]["start"] = src_a
                    s_new["source_timerange"]["duration"] = int(round(dur * toc))
                giu.append(s_new)

    # 2. Lấy các segment của bản mới nằm trong các khoảng chép sang
    vl_moi, vl_ra = _vat_lieu(moi), _vat_lieu(ra)
    them = 0
    for s in t_moi["segments"]:
        a = s["target_timerange"]["start"]
        b = a + s["target_timerange"]["duration"]
        for k0, k1 in khoang_us:
            overlap_a = max(a, k0)
            overlap_b = min(b, k1)
            dur = overlap_b - overlap_a
            if dur > 1000:
                s_new = copy.deepcopy(s)
                toc = float(s_new.get("speed") or 1.0)
                offset = overlap_a - a
                s_new["target_timerange"]["start"] = overlap_a
                s_new["target_timerange"]["duration"] = dur
                if s_new.get("source_timerange"):
                    src_old = s_new["source_timerange"].get("start", 0)
                    s_new["source_timerange"]["start"] = int(round(src_old + offset * toc))
                    s_new["source_timerange"]["duration"] = int(round(dur * toc))

                # Copy vật liệu tham chiếu
                for mid in [s_new.get("material_id")] + list(s_new.get("extra_material_refs") or []):
                    if mid and mid not in vl_ra and mid in vl_moi:
                        k_mat, m_mat = vl_moi[mid]
                        ra.setdefault("materials", {}).setdefault(k_mat, []).append(copy.deepcopy(m_mat))
                        vl_ra[mid] = (k_mat, m_mat)

                giu.append(s_new)
                them += 1

    t_ra["segments"] = sorted(giu, key=lambda x: x["target_timerange"]["start"])
    het = max((s["target_timerange"]["start"] + s["target_timerange"]["duration"] for t in ra.get("tracks", [])
               for s in t.get("segments", [])), default=0)
    ra["duration"] = max(int(ra.get("duration") or 0), het)
    return ra, them


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--goc", required=True, help="bản nháp người dùng đang sửa tay (chỉ đọc)")
    ap.add_argument("--moi", required=True, help="bản nháp mới dựng lại")
    ap.add_argument("--ten", required=True, help="tên bản nháp kết quả (phải chưa có)")
    ap.add_argument("--moc", type=float, default=None, help="giây: từ đây trở đi lấy hình của bản mới")
    ap.add_argument("--khoang", default=None, help="danh sách khoảng JSON [[a1, b1], [a2, b2], ...] (giây)")
    ap.add_argument("--drafts", default=None)
    a = ap.parse_args()
    if a.drafts is None:
        from common import thu_muc_nhap_capcut
        a.drafts = thu_muc_nhap_capcut()
    p_goc, p_moi, p_ra = (os.path.join(a.drafts, x) for x in (a.goc, a.moi, a.ten))
    if os.path.exists(p_ra):
        raise SystemExit(f"bản nháp '{a.ten}' đã có — chọn tên khác (không ghi đè)")
    goc, moi = _doc(os.path.join(p_goc, "draft_content.json")), _doc(os.path.join(p_moi, "draft_content.json"))

    if a.khoang:
        try:
            ds_khoang = json.loads(a.khoang) if not os.path.isfile(a.khoang) else _doc(a.khoang)
        except Exception as e:
            raise SystemExit(f"Lỗi tham số --khoang: {e}")
        ra, them = ghep_khoang(goc, moi, ds_khoang)
        kieu_txt = f"{len(ds_khoang)} khoảng"
    elif a.moc is not None:
        ra, them = ghep(goc, moi, a.moc)
        kieu_txt = f"từ mốc {a.moc:.1f} s"
    else:
        raise SystemExit("Cần truyền --moc hoặc --khoang")

    shutil.copytree(p_goc, p_ra)
    for f in [os.path.join(p_ra, "draft_content.json")] + glob.glob(os.path.join(p_ra, "Timelines", "*", "draft_content.json")):
        _ghi(f, ra)
        if os.path.isfile(f + ".bak"):
            os.remove(f + ".bak")
    pm = os.path.join(p_ra, "draft_meta_info.json")
    m = _doc(pm)
    m.update(draft_name=a.ten, draft_id=str(uuid.uuid4()).upper(), draft_fold_path=p_ra.replace("\\", "/"))
    _ghi(pm, m)
    # vật liệu mới vào khung 'Phương tiện' (kéo đoạn khác của video gốc được)
    import dung_tay
    files = sorted({v.get("path") for v in moi.get("materials", {}).get("videos", []) if v.get("path")})
    dung_tay._sua_nhap(p_ra, files)                          # noqa: SLF001
    print(f"xong: '{a.ten}' = '{a.goc}' + {them} đoạn hình của '{a.moi}' ({kieu_txt})")


if __name__ == "__main__":
    main()
