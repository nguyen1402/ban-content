# -*- coding: utf-8 -*-
"""TẠO HÀNG LOẠT ẢNH QUA GOOGLE FLOW (Nano Banana, 0 điểm).
Chạy qua giao diện web hoặc chạy trực tiếp bằng dòng lệnh (script).

Cách dùng dòng lệnh:
    python flow_hang_loat.py danh_sach.txt --ti-le 16:9 --thu ra/anh_flow
    python flow_hang_loat.py --prompts "con mèo tam thể\nphi thuyền không gian" --ti-le 9:16
"""
import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import common
import flow_ve

# --------------------------------------------------------------------------- PHÂN TÍCH PROMPT
def _slug_ten(s, max_len=30):
    s = re.sub(r"[^\w.-]+", "_", str(s or "").strip(), flags=re.U).strip("_")
    return s[:max_len] or "anh"


def tach_danh_sach_prompt(van_ban):
    """Tách văn bản thành danh sách [{id, ten_file, prompt}].
    Hỗ trợ các định dạng:
      1. Mỗi dòng một câu
      2. Đánh số: "1. Câu prompt..." hoặc "1) Câu prompt..."
      3. Tên file đặt trước: "01_meo: Chú mèo tam thể..." hoặc "hinh1.png | Câu prompt..."
    """
    van_ban = str(van_ban or "").replace("\\r\\n", "\n").replace("\\n", "\n")
    cac_dong = [d.strip() for d in van_ban.splitlines() if d.strip()]
    ket_qua = []
    stt = 1
    for dong in cac_dong:
        # Bỏ qua dòng ghi chú bắt đầu bằng # hoặc //
        if dong.startswith("#") or dong.startswith("//"):
            continue

        # Định dạng: "ten_file: prompt" hoặc "ten_file | prompt"
        m_ten = re.match(r"^([a-zA-Z0-9_-]{1,40}(?:\.png|\.jpg)?)\s*[:|]\s*(.+)$", dong)
        if m_ten:
            ten_file = m_ten.group(1).strip()
            prompt = m_ten.group(2).strip()
            if not (ten_file.endswith(".png") or ten_file.endswith(".jpg")):
                ten_file = f"{ten_file}.png"
        else:
            # Bỏ đánh số đầu dòng: "1.", "1)", "[1]"
            prompt = re.sub(r"^(?:\[?\d+[\].):-]\s*|-|\*)\s*", "", dong).strip()
            if not prompt:
                continue
            slug_doan = _slug_ten(prompt, 24)
            ten_file = f"{stt:03d}_{slug_doan}.png"

        ket_qua.append({
            "id": stt,
            "ten_file": ten_file,
            "prompt": prompt,
        })
        stt += 1

    return ket_qua


def kiem_tra_anh_hop_le(p):
    if not p or not os.path.isfile(p):
        return False
    if os.path.getsize(p) < 4000:
        return False
    return True


# --------------------------------------------------------------------------- TIẾN TRÌNH TẠO HÀNG LOẠT
class FlowBatchRunner:
    """Bộ điều phối chạy script tạo hàng loạt ảnh qua Flow."""

    def __init__(self):
        self._khoa = threading.RLock()
        self.dang_chay = False
        self.da_dung = False
        self.tong = 0
        self.da_xong = 0
        self.loi = 0
        self.hien_tai = 0
        self.thoi_gian_bat_dau = 0.0
        self.thoi_gian_cap_nhat = 0.0
        self.thu_muc = ""
        self.ti_le = "16:9"
        self.tien_to = ""
        self.hau_to = ""
        self.cac_muc = []       # [{id, ten_file, prompt, prompt_day_du, trang_thai, loi, tep, url, thoi_gian, ho_so}]
        self.log_lines = []
        self._thread = None

    def _ghi_log(self, msg):
        t = time.strftime("%H:%M:%S")
        line = f"[{t}] {msg}"
        with self._khoa:
            self.log_lines.append(line)
            if len(self.log_lines) > 200:
                self.log_lines = self.log_lines[-200:]
            self.thoi_gian_cap_nhat = time.time()
        common.log(line)

    def _luu_so(self):
        """Lưu danh_sach.json vào thư mục xuất ảnh để lưu vết kết quả."""
        if not self.thu_muc:
            return
        try:
            os.makedirs(self.thu_muc, exist_ok=True)
            p = os.path.join(self.thu_muc, "danh_sach.json")
            data = {
                "tong": self.tong,
                "da_xong": self.da_xong,
                "loi": self.loi,
                "ti_le": self.ti_le,
                "tien_to": self.tien_to,
                "hau_to": self.hau_to,
                "thoi_gian_bat_dau": self.thoi_gian_bat_dau,
                "thoi_gian_cap_nhat": self.thoi_gian_cap_nhat,
                "cac_muc": self.cac_muc,
            }
            common.ghi_json(p, data)
        except Exception:                                    # noqa: BLE001
            pass

    def lay_trang_thai(self):
        with self._khoa:
            return {
                "dang_chay": self.dang_chay,
                "da_dung": self.da_dung,
                "tong": self.tong,
                "da_xong": self.da_xong,
                "loi": self.loi,
                "hien_tai": self.hien_tai,
                "thoi_gian_bat_dau": self.thoi_gian_bat_dau,
                "thoi_gian_cap_nhat": self.thoi_gian_cap_nhat,
                "thu_muc": self.thu_muc,
                "ti_le": self.ti_le,
                "cac_muc": list(self.cac_muc),
                "log": list(self.log_lines[-60:]),
            }

    def dung(self):
        """Yêu cầu dừng tiến trình sau câu đang chạy."""
        with self._khoa:
            if self.dang_chay:
                self.da_dung = True
                self._ghi_log("⚠️ Đang yêu cầu dừng tạo hàng loạt...")
                return True
        return False

    def bat_dau(self, prompts_text, thu_muc, ti_le="16:9", tien_to="", hau_to="", chi_chay_lai_loi=False):
        """Khởi động lượt tạo ảnh hàng loạt."""
        with self._khoa:
            if self.dang_chay:
                raise RuntimeError("Tiến trình tạo hàng loạt đang chạy")

            import chinh_sua.anh_ve as av
            co_flow = flow_ve.co_ho_so()
            co_gemini = bool(av._tai_khoan())

            if not co_flow and not co_gemini:
                raise RuntimeError("Chưa có hồ sơ Chrome Flow (0 điểm) lẫn tài khoản Gemini (cookie). Hãy tạo hồ sơ Flow hoặc thêm cookie trước.")

            if chi_chay_lai_loi and self.cac_muc:
                # Giữ nguyên danh sách cũ, chỉ đặt lại các mục lỗi sang chờ
                cac_muc_chay = [m for m in self.cac_muc if m["trang_thai"] == "loi"]
                if not cac_muc_chay:
                    raise RuntimeError("Không có câu nào bị lỗi để chạy lại.")
                for m in cac_muc_chay:
                    m["trang_thai"] = "cho"
                    m["loi"] = ""
            else:
                ds = tach_danh_sach_prompt(prompts_text)
                if not ds:
                    raise RuntimeError("Không tìm thấy câu lệnh tạo ảnh nào hợp lệ.")

                self.cac_muc = []
                for x in ds:
                    prompt_day_du = f"{tien_to.strip()} {x['prompt'].strip()} {hau_to.strip()}".strip()
                    self.cac_muc.append({
                        "id": x["id"],
                        "ten_file": x["ten_file"],
                        "prompt": x["prompt"],
                        "prompt_day_du": prompt_day_du,
                        "trang_thai": "cho",          # cho | dang | xong | loi
                        "loi": "",
                        "tep": "",
                        "url": "",
                        "thoi_gian": 0,
                        "ho_so": "",
                    })

            self.thu_muc = os.path.abspath(thu_muc)
            os.makedirs(self.thu_muc, exist_ok=True)
            self.ti_le = str(ti_le or "16:9")
            self.tien_to = str(tien_to or "")
            self.hau_to = str(hau_to or "")
            self.tong = len(self.cac_muc)
            self.da_xong = sum(1 for m in self.cac_muc if m["trang_thai"] == "xong")
            self.loi = sum(1 for m in self.cac_muc if m["trang_thai"] == "loi")
            self.hien_tai = 0
            self.dang_chay = True
            self.da_dung = False
            self.thoi_gian_bat_dau = time.time()
            self.thoi_gian_cap_nhat = time.time()
            self.log_lines = []

        self._ghi_log(f"🚀 Bắt đầu tạo {len([m for m in self.cac_muc if m['trang_thai'] == 'cho'])} ảnh qua Flow (tỉ lệ: {self.ti_le}, lưu tại: {self.thu_muc})")
        self._luu_so()

        self._thread = threading.Thread(target=self._chay_vong_lap, daemon=True)
        self._thread.start()
        return True

    def _so_luong(self):
        """22/10 user ("nhiều luồng, nhiều cookie được nghỉ"): số luồng = số hồ sơ Flow không nghỉ (có Flow) hoặc số
        tài khoản Gemini cookie dùng được; tối đa 8."""
        try:
            if flow_ve.co_ho_so():
                return max(1, min(8, flow_ve.so_ho_so_dung_duoc()))
            import chinh_sua.anh_ve as av
            return max(1, min(8, av.so_luong_ve()))
        except Exception:                                    # noqa: BLE001
            return 1

    def _lam_mot(self, idx, muc):
        """Tạo MỘT ảnh (chạy trong luồng song song)."""
        with self._khoa:
            if self.da_dung:
                return
            if muc["trang_thai"] == "xong":
                return

            self.hien_tai = idx + 1
            muc["trang_thai"] = "dang"
            muc["loi"] = ""
            self.thoi_gian_cap_nhat = time.time()

        t0 = time.time()
        prompt_day_du = muc["prompt_day_du"]
        ten_file = muc["ten_file"]
        self._ghi_log(f"[{idx+1}/{self.tong}] Đang tạo '{ten_file}': {muc['prompt'][:70]}...")

        tep_ra = None
        loi_msg = ""
        ho_so_ve = ""
        try:
            if flow_ve.co_ho_so():
                so_truoc = flow_ve._doc_so()             # noqa: SLF001
                tep_ra = flow_ve.ve(prompt_day_du, self.thu_muc, ten_file, ti_le=self.ti_le)
                so_sau = flow_ve._doc_so()              # noqa: SLF001
                for k, v in so_sau.items():
                    if int(v.get("so_anh", 0)) > int(so_truoc.get(k, {}).get("so_anh", 0)):
                        ho_so_ve = f"Flow ({k})"     # (chạy song song: chỉ để hiển thị, có thể lệch hồ sơ)
                        break
            if not tep_ra:
                import chinh_sua.anh_ve as av
                if av._tai_khoan():
                    self._ghi_log("  → Chạy qua Gemini (cookie)...")
                    tep_ra = av.ve_prompt(prompt_day_du, self.thu_muc, ten_file)
                    if tep_ra:
                        ho_so_ve = "Gemini"
        except Exception as e:                       # noqa: BLE001
            loi_msg = str(e)

        dt = round(time.time() - t0, 1)

        with self._khoa:
            muc["thoi_gian"] = dt
            muc["ho_so"] = ho_so_ve
            if tep_ra and kiem_tra_anh_hop_le(tep_ra):
                muc["trang_thai"] = "xong"
                muc["tep"] = tep_ra
                muc["url"] = f"/file?p={common.ma_hoa_url(tep_ra)}" if hasattr(common, "ma_hoa_url") else f"/file?p={urllib_quote(tep_ra)}"
                self.da_xong += 1
                self._ghi_log(f"  ✔ [{idx+1}/{self.tong}] Đã tạo xong '{ten_file}' ({dt}s){' qua ' + ho_so_ve if ho_so_ve else ''}")
            else:
                muc["trang_thai"] = "loi"
                if tep_ra and os.path.isfile(tep_ra):
                    try:
                        os.remove(tep_ra)
                    except OSError:
                        pass
                if not loi_msg:
                    # Lấy lỗi từ sổ hồ sơ nếu có
                    d_so = flow_ve._doc_so()        # noqa: SLF001
                    cac_loi = [v.get("loi") for v in d_so.values() if v.get("loi")]
                    loi_msg = cac_loi[0] if cac_loi else "Không nhận được file ảnh hợp lệ"
                muc["loi"] = loi_msg
                self.loi += 1
                self._ghi_log(f"  ✖ [{idx+1}/{self.tong}] Lỗi tạo '{ten_file}': {loi_msg[:120]}")

            self.thoi_gian_cap_nhat = time.time()
        self._luu_so()

        time.sleep(0.5)                                     # nghỉ nhẹ trước ảnh kế của luồng này

    def _chay_vong_lap(self):
        try:
            cho = [(idx, m) for idx, m in enumerate(self.cac_muc) if m["trang_thai"] != "xong"]
            n = self._so_luong()
            self._ghi_log(f"  chạy SONG SONG {n} luồng (mỗi luồng giữ một hồ sơ Flow / tài khoản Gemini rảnh)")
            with ThreadPoolExecutor(n) as ex:
                list(ex.map(lambda x: self._lam_mot(*x), cho))
            if self.da_dung:
                self._ghi_log("🛑 Đã dừng tạo hàng loạt theo yêu cầu của bạn.")

            with self._khoa:
                self.dang_chay = False
                tong_time = round(time.time() - self.thoi_gian_bat_dau, 1)
                self._ghi_log(f"🏁 Kết thúc: {self.da_xong}/{self.tong} ảnh thành công, {self.loi} ảnh lỗi (tổng thời gian: {tong_time}s).")
            self._luu_so()

        except Exception as e:                               # noqa: BLE001
            with self._khoa:
                self.dang_chay = False
                self._ghi_log(f"💥 Lỗi luồng tạo hàng loạt: {e}")
            self._luu_so()


def urllib_quote(p):
    import urllib.parse
    return urllib.parse.quote(p, safe="")


# Singleton quản lý lượt chạy
_RUNNER = FlowBatchRunner()


def lay_runner():
    return _RUNNER


# --------------------------------------------------------------------------- CLI COMMAND LINE
def main():
    parser = argparse.ArgumentParser(description="Tạo hàng loạt ảnh bằng Google Flow (Nano Banana, 0 điểm)")
    parser.add_argument("tep_hoac_prompts", nargs="?", default="", help="Đường dẫn file .txt chứa câu lệnh hoặc câu lệnh trực tiếp")
    parser.add_argument("--prompts", default="", help="Nội dung danh sách câu prompt (mỗi dòng một câu)")
    parser.add_argument("--ti-le", default="16:9", choices=["16:9", "9:16", "1:1", "4:3", "3:4"], help="Tỉ lệ ảnh (16:9, 9:16, 1:1, 4:3, 3:4)")
    parser.add_argument("--thu", default="ra/anh_flow", help="Thư mục lưu ảnh kết quả (mặc định ra/anh_flow)")
    parser.add_argument("--tien-to", default="", help="Tiền tố ghép vào trước mỗi prompt")
    parser.add_argument("--hau-to", default="", help="Hậu tố phong cách ghép vào sau mỗi prompt")

    args = parser.parse_args()

    noi_dung = args.prompts
    if not noi_dung and args.tep_hoac_prompts:
        if os.path.isfile(args.tep_hoac_prompts):
            with open(args.tep_hoac_prompts, encoding="utf-8-sig") as f:
                noi_dung = f.read()
        else:
            noi_dung = args.tep_hoac_prompts

    if not noi_dung:
        parser.print_help()
        sys.exit(1)

    print("=== TẠO HÀNG LOẠT ẢNH QUA GOOGLE FLOW ===")
    runner = lay_runner()
    runner.bat_dau(noi_dung, thu_muc=args.thu, ti_le=args.ti_le, tien_to=args.tien_to, hau_to=args.hau_to)

    while runner.dang_chay:
        time.sleep(1)

    st = runner.lay_trang_thai()
    print(f"\nKết quả: {st['da_xong']}/{st['tong']} ảnh thành công, {st['loi']} lỗi.")
    print(f"Thư mục ảnh: {st['thu_muc']}")


if __name__ == "__main__":
    main()
