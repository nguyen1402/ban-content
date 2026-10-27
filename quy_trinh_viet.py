# -*- coding: utf-8 -*-
"""QUY TRÌNH VIẾT KỊCH BẢN CỦA NGƯỜI DÙNG — 26/10/2026 user (làm tay trên Gemini, nay app làm lần lượt):

  CHAT A (một cuộc chat, chờ trả lời xong mới gửi tiếp — Gemini nhớ dàn ý và bài đã viết):
    1. lập DÀN Ý A (theo ADN kênh, hoặc từ transcript gốc khi viết lại)
    2. viết BÀI GỐC từng phần
    3. "Lệnh 5.x": dán bài gốc phần i + câu lệnh viết lại phần i sâu sắc hơn (phần 1 kèm kêu gọi đăng ký)
    4. "Phần End": đúc kết + bài học + câu hỏi bình luận + kêu gọi đăng ký
    5. "Phần Hook": đoạn hook 50-70 từ
  CHAT B (cuộc chat MỚI): viết lại chi tiết, dễ hiểu, đổi đơn vị Mỹ, bỏ ký hiệu để AI đọc — lần lượt từng khúc:
    hook + phần 1, phần 2, …, phần cuối + end.
  Chỉ chạy trên tài khoản Gemini PRO (gemini_chrome.ho_so_pro); model mặc định 3.8 Flash (26/10 user: "bản pro 3.1 không
  bằng flash 3.8" — đo: Pro 3.1 trả câu từ chối soạn sẵn liên tục với câu lệnh dàn ý), chọn được Pro trên giao diện.

Câu lệnh mẫu là NGUYÊN VĂN câu lệnh của người dùng (sửa được trên giao diện, lưu cache/mau_quy_trinh.json).
Chỗ trống: {i} số phần, {so_tu} số từ, {nguon_du_kien} câu "chỉ lấy dữ kiện từ…" (transcript gốc / dàn ý A)."""
import os
import re
import threading
import time

from common import CACHE_CHUNG, ROOT, doc_json, ghi_json, log

MAU_FILE = os.path.join(CACHE_CHUNG, "mau_quy_trinh.json")
# 26/10 chạy thật: câu lệnh End / Hook không nhắc tới bài đang viết -> Gemini trả câu lỗi / từ chối; thêm câu dẫn phía trước
DAN_END_HOOK = "Dựa trên toàn bộ bài đã viết lại ở trên:\n"

_KHONG_LAP = (" Đặc biệt, không được viết lặp lại từ, không được lặp lại câu hay cấu trúc lặp, nói chung không được lặp "
              "những từ ngữ giống nhau quá nhiều mà thay thế bằng những cách diễn đạt đa dạng hơn để tránh nhàm chán cho "
              "khán giả.\n LƯU Ý, không lặp lại các từ ngữ có 2 đến 3 từ liên tục trong 1 đoạn, hoặc 1 phần quá 2 lần.\n"
              " Trả lời trực tiếp trong khung chat. Trả lời rồi dừng lại.")
_THAN = (" Hãy viết lại phần thứ {i} sâu sắc và có chiều sâu hơn.\n"
         " Hãy viết mạch lạc và viết bài xuyên suốt, không chia từng phần, không dùng icon.\n"
         " Hãy viết với văn phong tự nhiên, không được quá văn chương.\n"
         " Không được chia quá nhiều đoạn (tối đa 6 đoạn).\n"
         " Nếu nội dung được viết ra có những \"con số\", thì hãy viết những con số ra bằng chữ.\n"
         " Hãy bám theo những ý đã liệt kê ở phần {i} của dàn ý A (phải đưa những thông số hay số liệu thống kê vào. "
         "{nguon_du_kien}).\n"
         " Viết bằng ngôn ngữ tiếng Việt với {so_tu} từ.\n"
         " Không để có điều gì vi phạm pháp luật tại Việt Nam.\n")

MAU_MAC_DINH = {
    # 26/10 user: "ADN để dựng dàn bài thì học theo kênh gốc, còn khi viết thì những câu lệnh của tôi chỉ BỔ TRỢ cho ADN
    # đó thôi" — ADN giọng văn của kênh là nền cho mọi bước viết ở chat A (chat B viết lại dễ hiểu thì không cần ADN)
    # 27/10 (chạy thật: tin "ghi nhớ… Chỉ trả lời: Đã nhận ADN" bị Gemini từ chối cả sau khi nhắc; user: "thay đổi cách
    # yêu cầu nó viết lại chắc nó đang bị hiểu sai") -> ADN thành đoạn NGỮ CẢNH đứng đầu lệnh viết bài gốc phần 1
    "nen_adn": ("PHONG CÁCH VIẾT CỦA KÊNH «{kenh}» (các phần của bài này đều viết theo phong cách này; các yêu cầu cụ "
                "thể ở mỗi lần nhờ viết chỉ bổ sung độ dài, số đoạn, cách viết số…):\n{adn}"),
    "nhac_adn": "(Viết đúng ADN kênh «{kenh}» đã nêu: giữ ngôi kể, giọng văn, nhịp câu của kênh; các yêu cầu dưới đây là bổ sung.)",
    "dan_bai_transcript": ("Dưới đây là TRANSCRIPT GỐC của một video. Hãy lập DÀN Ý A gồm đúng {so_phan} phần để viết lại "
                           "thành video mới khoảng {tong_tu} từ, theo phong cách kênh «{kenh}». Mỗi phần ghi rõ: "
                           "PHẦN số: tên phần (~số từ), rồi các ý chính kèm thông số, số liệu có trong transcript. "
                           "Không dùng icon. Trả lời rồi dừng lại.\n\nTRANSCRIPT GỐC:\n{transcript}"),
    "viet_goc": ("Dựa trên DÀN Ý A ở trên, hãy viết BÀI GỐC cho PHẦN {i} ({ten_phan}) khoảng {so_tu} từ, tiếng Việt, "
                 "văn xuôi liền mạch, không tiêu đề, không icon. Chỉ viết đúng phần {i}. Trả lời rồi dừng lại."),
    "sau_sac_phan_1": (_THAN + " Sau khi kết thúc phần 1, hãy kêu gọi đăng ký kênh để ủng hộ chúng mình có động lực làm "
                       "tiếp các video hay sau này.\n" + _KHONG_LAP),
    "sau_sac": _THAN + _KHONG_LAP,
    "end": ("Hãy viết một đoạn đúc kết dài 50 từ. Sau đó, hãy đưa ra bài học sâu sắc rút ra và cách áp dụng nó vào cuộc "
            "sống hiện tại cho khán giả. Hãy lược bỏ những cụm từ \"bài học sâu sắc, cách áp dụng thực tế\"\n"
            "Không được viết lặp lại từ, lặp lại câu, tránh gây nhàm chán cho khán giả.\n"
            "Sau khi viết hết phần này, hãy tạo ra 1 câu hỏi đơn giản, dễ trả lời và yêu cầu họ bình luận xuống bên dưới "
            "video để trả lời quan điểm của họ để mọi người cùng tham khảo ý kiến, sau đó kêu gọi đăng ký kênh để ủng hộ "
            "kênh có động lực làm tiếp nội dung hay tiếp theo!"),
    "hook": ("Viết 1 đoạn HOOK mạnh; khoảng 50 - 70 từ gây ra sự tò mò, bí ẩn, thu hút, gây ra cảm xúc mạnh, gây sốc ngay "
             "từ ban đầu để HOOK vào tâm trí khán giả, khiến họ không cưỡng lại được mà thôi thúc nghe câu chuyện đến cuối "
             "video để xem đoạn kết.\nKhông được sử dụng những câu: bạn có biết rằng, bạn hãy tưởng tượng\n"
             "Hãy viết với văn phong tự nhiên, không mang tính học thuật và đơn giản dễ hiểu, đi vào trọng tâm."),
    "viet_lai": ("Hãy viết lại đoạn này chi tiết và dễ hiểu hơn (không được quá văn chương). Hãy viết với văn phong tự nhiên "
                 "(không được cứng nhắc và thiếu hợp lý như máy móc). Hãy qui đổi các đơn vị của Mỹ sang Việt Nam (như dặm "
                 "sang km, acres sang hecta). Trả lời trực tiếp trong khung chat. Không được dùng Icon hay biểu tượng như "
                 "(-,*). Không sử dụng dấu hai chấm \":\", dấu ngoặc đơn () hoặc ngoặc kép\"\", vì sẽ sử dụng AI để đọc:"),
    # 27/10 user: bài viral thì "phát triển tiếp" phần 2, phần 3… — dàn ý A của phần mới nối tiếp các phần trước
    "dan_bai_phan_tiep": ("Video «{tieu_de}» của kênh «{kenh}» đang được khán giả đón nhận. Hãy lập DÀN Ý A cho PHẦN "
                          "{phan_so} — video nối tiếp — gồm đúng {so_phan} phần, khoảng {tong_tu} từ. Phát triển tiếp câu "
                          "chuyện / chủ đề: đào sâu khía cạnh mới, tình tiết mới, không lặp lại ý, ví dụ, số liệu đã dùng ở "
                          "các phần trước; đoạn mở đầu nối với phần trước. Mỗi phần ghi rõ: PHẦN số: tên phần (~số từ), "
                          "rồi các ý chính kèm thông số, số liệu. Không dùng icon. Trả lời rồi dừng lại.\n\n"
                          "CÁC PHẦN TRƯỚC ĐÃ LÀM:\n{phan_truoc}"),
    "nguon_transcript": "Chỉ lấy thông tin có trong transcript gốc, KHÔNG BỔ SUNG DỮ KIỆN NGOÀI",
    "nguon_dan_bai": "Chỉ lấy thông tin có trong dàn ý A và bài gốc, KHÔNG BỔ SUNG DỮ KIỆN NGOÀI",
}
TEN_MAU = {"nen_adn": "Phong cách kênh (gửi kèm lệnh viết bài gốc phần 1, chat A)",
           "nhac_adn": "Câu nhắc ADN đứng trước mỗi câu lệnh viết","dan_bai_transcript": "Lập dàn ý A từ transcript (chế độ viết lại)",
           "dan_bai_phan_tiep": "Lập dàn ý A cho phần tiếp (phần 2, 3… của bài viral)", "viet_goc": "Viết bài gốc từng phần",
           "sau_sac_phan_1": "Lệnh 5 — phần 1 (kèm kêu gọi đăng ký)", "sau_sac": "Lệnh 5.x — các phần sau",
           "end": "Phần End", "hook": "Phần Hook", "viet_lai": "Viết lại chi tiết, dễ hiểu (chat mới)",
           "nguon_transcript": "Câu giới hạn dữ kiện — khi có transcript", "nguon_dan_bai": "Câu giới hạn dữ kiện — ý tưởng mới"}


def doc_mau():
    """Câu lệnh mẫu: bản người dùng đã sửa (cache/mau_quy_trinh.json), thiếu mục nào lấy mặc định."""
    d = doc_json(MAU_FILE, {}) or {}
    return {k: (d.get(k) if str(d.get(k) or "").strip() else v) for k, v in MAU_MAC_DINH.items()}


def luu_mau(mau):
    d = {k: str(v) for k, v in (mau or {}).items() if k in MAU_MAC_DINH and str(v).strip() and v != MAU_MAC_DINH[k]}
    os.makedirs(os.path.dirname(MAU_FILE), exist_ok=True)
    ghi_json(MAU_FILE, d)
    return doc_mau()


def _dien(mau, **kw):
    """Điền chỗ trống {ten}; chỗ trống không có giá trị giữ nguyên (người dùng tự viết dấu ngoặc nhọn vẫn an toàn)."""
    return re.sub(r"\{(\w+)\}", lambda m: str(kw[m.group(1)]) if m.group(1) in kw else m.group(0), mau)


def _sach(t):
    return re.sub(r"\n{3,}", "\n\n", str(t or "").replace("**", "")).strip()


def _gui(phien, text, bao, so_lan=2, toi_thieu=0):
    """Một lượt chat. Treo / lỗi (26/10: lượt End treo làm mất cả bài) -> MỞ LẠI đúng cuộc chat theo ID (user: "lưu lại ID
    chat xong mở lại vào viết vẫn ok"): câu trả lời đã có thì lấy luôn, chưa có thì gửi lại câu đó — tối đa so_lan lần.
    toi_thieu: số từ tối thiểu — 26/10 chạy thật: End = "I encountered an error… try again?", Hook = "Tôi không được lập
    trình để làm điều đó." (câu lỗi / từ chối không đoán hết được) -> trả lời ngắn hơn yêu cầu nhiều = lượt hỏng."""
    def du(kq):
        if toi_thieu and len(str(kq or "").split()) < toi_thieu:
            raise RuntimeError(f"trả lời quá ngắn ({len(str(kq or '').split())}/{toi_thieu} từ): {str(kq)[:60]}")
        return kq
    for lan in range(so_lan + 1):
        try:
            return du(phien.gui(text))
        except (TimeoutError, RuntimeError, OSError, ValueError) as e:
            if lan == so_lan:
                raise
            if not phien.url:                                # lượt đầu chưa có ID chat: gửi lại trên tab đang mở
                bao(f"  ↻ Gemini lỗi ({str(e)[:80]}) — gửi lại…")
                continue
            bao(f"  ↻ Gemini lỗi ({str(e)[:80]}) — mở lại chat theo ID rồi viết tiếp…")
            try:
                phien.mo_lai()
                co = phien.tra_loi_cho(text)
            except (TimeoutError, RuntimeError, OSError, ValueError) as e2:
                bao(f"  ! mở lại chat lỗi ({str(e2)[:80]}) — thử lượt kế")
                continue
            if co and not (toi_thieu and len(co.split()) < toi_thieu):
                bao("  ✔ câu trả lời đã có trong chat — lấy luôn, không gửi lại")
                return co


def _dung_dinh_dang(kq, so_phan):
    """Dàn ý A có ít nhất 2 phần ghi nhãn "PHẦN n" (26/10: Gemini trả câu từ chối, bộ tách vẫn coi một dòng là "phần 1"
    và cả quy trình viết theo câu đó)."""
    return len(re.findall(r"(?im)^\W*(?:PHẦN|HỒI|CHƯƠNG)\s*\d+", kq or "")) >= min(2, so_phan)


def _mo_chat_a(G, ten, cong, model, lenh, dat, bao, so_chat=3):
    """Lượt ĐẦU của chat A (dàn ý A). 26/10 đo: chat đã bị Gemini từ chối thì gửi lại trong chat đó vẫn từ chối (4 lần
    liền) -> bỏ chat đó, mở CHAT MỚI gửi lại. -> (phiên, câu trả lời)."""
    ly_do = ""
    for k in range(so_chat):
        p = G.PhienChat(ten, cong, model=model)
        try:
            kq = p.gui(lenh)
            if dat(kq):
                return p, kq
            ly_do = f"dàn ý sai định dạng ({len(kq)} ký tự)"
        except (TimeoutError, RuntimeError, OSError, ValueError) as e:
            ly_do = str(e)[:90]
        p.dong()
        bao(f"  ↻ chat A lần {k + 1}: {ly_do} — mở chat MỚI gửi lại…")
    raise RuntimeError(f"Gemini không lập được dàn ý A sau {so_chat} chat ({ly_do})")


# --------------------------------------------------------------------------- KHO BÀI VIẾT
# 27/10 user: "có dàn bài rồi mà không thấy thư mục nào lưu dàn bài vào để nhỡ bị thoát thì vẫn còn dàn bài lần sau viết
# tiếp, cả bài hoàn thiện nữa" -> mỗi bài một thư mục kich_ban/bai_viet/<mã>/: trang_thai.json (mọi bước, ID chat A/B
# để mở lại đúng cuộc chat), dan_bai.txt, cac_buoc.txt, bai_hoan_chinh.txt. Ghi lại sau TỪNG bước của quy trình.
KHO = os.path.join(ROOT, "kich_ban", "bai_viet")
_DANG_VIET = set()                                           # mã bài đang chạy quy trình (không cho chạy chồng)
_KHOA_KHO = threading.Lock()


def _thu_muc(ma):
    return os.path.join(KHO, re.sub(r"[^\w.-]+", "_", str(ma or ""), flags=re.U))


def tao_bai(tieu_de, plugin, dan_bai="", transcript="", tham=None, phan_so=1, goc="", phan_truoc=""):
    ten = re.sub(r"[^\w]+", "_", str(tieu_de or "bai").lower(), flags=re.U).strip("_")[:40] or "bai"
    ma = time.strftime("%Y%m%d_%H%M%S_") + ten + (f"_phan{int(phan_so)}" if int(phan_so or 1) > 1 else "")
    goc_ma, k = ma, 1
    while os.path.exists(_thu_muc(ma)):                      # cùng giây, cùng tiêu đề: thêm hậu tố, không ghi đè bài cũ
        k += 1
        ma = f"{goc_ma}_{k}"
    bai = {"ma": ma, "tieu_de": str(tieu_de or "").strip(),
           "kenh": (plugin or {}).get("kenh_ten") or "", "plugin": plugin or {}, "tham": dict(tham or {}),
           "transcript": str(transcript or ""), "phan_so": int(phan_so or 1), "goc": goc, "phan_truoc": phan_truoc,
           "tao": time.time(), "dan_bai": str(dan_bai or "").strip(), "ban_goc": [], "sau_sac": [], "end": "", "hook": "",
           "viet_lai": [], "chat_a": "", "chat_b": "", "da_adn": False, "ho_so": "", "kich_ban": "", "loi": ""}
    luu_bai(bai)
    return bai


def luu_bai(bai):
    """Ghi trang_thai.json + các tệp đọc được (dan_bai.txt, cac_buoc.txt, bai_hoan_chinh.txt)."""
    bai["cap_nhat"] = time.time()
    tm = _thu_muc(bai["ma"])
    with _KHOA_KHO:
        os.makedirs(tm, exist_ok=True)
        ghi_json(os.path.join(tm, "trang_thai.json"), bai)

        def ghi(ten, t):
            if str(t or "").strip():
                with open(os.path.join(tm, ten), "w", encoding="utf-8") as f:
                    f.write(str(t).strip() + "\n")
        dau = bai["tieu_de"] + (f" — PHẦN {bai['phan_so']}" if int(bai.get("phan_so") or 1) > 1 else "")
        ghi("dan_bai.txt", bai["dan_bai"] and f"{dau}\n\n{bai['dan_bai']}")
        cac = [("DÀN Ý A", bai["dan_bai"])] + [(f"BÀI GỐC PHẦN {i + 1}", t) for i, t in enumerate(bai["ban_goc"])] \
            + [(f"SÂU SẮC HƠN PHẦN {i + 1}", t) for i, t in enumerate(bai["sau_sac"])] + [("END", bai["end"]), ("HOOK", bai["hook"])] \
            + [(f"VIẾT LẠI DỄ HIỂU — KHÚC {i + 1}", t) for i, t in enumerate(bai["viet_lai"])]
        ghi("cac_buoc.txt", "\n\n".join(f"===== {k} =====\n{t}" for k, t in cac if str(t or "").strip()))
        ghi("bai_hoan_chinh.txt", bai["kich_ban"])


def doc_bai(ma):
    return doc_json(os.path.join(_thu_muc(ma), "trang_thai.json"), None)


def tinh_trang(bai):
    """'xong' | 'dang' (viết dở) | 'dan_bai' (mới có dàn bài) | 'trong'."""
    if bai.get("kich_ban"):
        return "xong"
    if bai.get("ban_goc") or bai.get("chat_a"):
        return "dang"
    return "dan_bai" if bai.get("dan_bai") else "trong"


def tom_tat(bai):
    """Bản gửi giao diện (bỏ plugin, transcript, các phần trước)."""
    ra = {k: v for k, v in bai.items() if k not in ("plugin", "transcript", "phan_truoc")}
    ra.update(tinh_trang=tinh_trang(bai), so_tu=len(str(bai.get("kich_ban") or "").split()),
              dang_chay=bai["ma"] in _DANG_VIET, thu_muc=_thu_muc(bai["ma"]))
    return ra


def ds_bai():
    ra = []
    for ten in os.listdir(KHO) if os.path.isdir(KHO) else []:
        b = doc_json(os.path.join(KHO, ten, "trang_thai.json"), None)
        if isinstance(b, dict) and b.get("ma"):
            t = tom_tat(b)
            for k in ("ban_goc", "sau_sac", "viet_lai", "end", "hook", "kich_ban", "dan_bai"):
                t.pop(k, None)
            t["so_phan_dan_bai"] = len(re.findall(r"(?im)^\W*(?:PHẦN|HỒI|CHƯƠNG)\s*\d+", b.get("dan_bai") or ""))
            ra.append(t)
    return sorted(ra, key=lambda b: -float(b.get("cap_nhat") or 0))


def tao_phan_tiep(ma):
    """Bài viral -> bài MỚI là phần kế tiếp (phần 2, 3…): cùng kênh / tham số, mang dàn ý + kịch bản các phần trước để
    Gemini lập dàn ý nối tiếp, không lặp lại."""
    goc = doc_bai(ma)
    if not goc:
        raise RuntimeError("không thấy bài " + str(ma))
    if not goc.get("kich_ban"):
        raise RuntimeError("bài này chưa viết xong — viết xong mới phát triển phần tiếp")
    chuoi, b = [], goc
    while b:                                                  # lần ngược các phần trước: phần 1 -> phần hiện tại
        chuoi.insert(0, b)
        b = doc_bai(b.get("goc")) if b.get("goc") else None
    truoc = "\n\n".join(f"===== PHẦN {x.get('phan_so', 1)} =====\nDÀN Ý:\n{x.get('dan_bai', '')}\n\nKỊCH BẢN:\n"
                        + str(x.get("kich_ban") or "")[:(8000 if x is goc else 2500)] for x in chuoi)
    return tao_bai(goc["tieu_de"], goc.get("plugin") or {}, tham=goc.get("tham"), phan_so=int(goc.get("phan_so") or 1) + 1,
                   goc=goc["ma"], phan_truoc=truoc)


def chay(tieu_de, plugin, dan_bai_text="", transcript="", tong_tu=None, so_tu_phan_1=300, so_tu_phan=500,
         y_tuong=None, bao=None, dung=lambda: False, model="flash", bai=None):
    """Chạy trọn quy trình -> bài (tom_tat: kich_ban, dan_bai, ban_goc[], sau_sac[], end, hook, viet_lai[], ho_so, giay…).
    bai: bài trong kho (doc_bai) — bước nào đã có thì BỎ QUA, mở lại đúng chat A / B theo ID để viết tiếp; không có thì
    tạo bài mới. Mỗi bước xong là ghi vào kho."""
    if bai is None:
        bai = tao_bai(tieu_de, plugin, dan_bai=dan_bai_text, transcript=transcript,
                      tham=dict(tong_tu=tong_tu, so_tu_phan_1=so_tu_phan_1, so_tu_phan=so_tu_phan, model=model))
    if bai["ma"] in _DANG_VIET:
        raise RuntimeError("bài này đang được viết ở một lượt khác")
    _DANG_VIET.add(bai["ma"])
    try:
        bai["loi"] = ""
        _chay(bai, y_tuong, bao or (lambda *_: None), dung, model, int(tong_tu or 0) or None, so_tu_phan_1, so_tu_phan)
        return tom_tat(bai)
    except Exception as e:
        bai["loi"] = str(e)[:300]
        raise
    finally:
        luu_bai(bai)
        _DANG_VIET.discard(bai["ma"])


def _chay(ra, y_tuong, bao, dung, model, tong_tu, so_tu_phan_1, so_tu_phan):
    import doi_thu
    import gemini_chrome as G
    tieu_de, plugin, transcript = ra["tieu_de"], ra.get("plugin") or {}, ra.get("transcript") or ""
    mau = doc_mau()
    t0 = time.time()
    bao("Tìm tài khoản Gemini PRO…")
    hs = G.ho_so_pro(bao=bao)
    if not hs:
        raise RuntimeError("không có hồ sơ Chrome nào là tài khoản Gemini PRO / Ultra (quy trình viết chỉ chạy trên Pro)")
    ten, cong = hs
    ra["ho_so"] = ten
    kenh = plugin.get("kenh_ten") or "kênh"
    nguon = mau["nguon_transcript"] if transcript.strip() else mau["nguon_dan_bai"]
    kb_kenh = plugin.get("kich_ban") or {}
    nen_adn = _dien(mau["nen_adn"], kenh=kenh, adn=doi_thu._phong_cach_viet(plugin))   # noqa: SLF001
    nhac = _dien(mau["nhac_adn"], kenh=kenh) + "\n"

    def luu():
        luu_bai(ra)

    def kiem_dung():
        if dung():
            raise RuntimeError("đã dừng theo yêu cầu")

    # ---------------- CHAT A: dàn ý A -> bài gốc -> sâu sắc -> end -> hook (cùng một cuộc chat)
    if not ra.get("viet_lai") and not (ra.get("hook") and ra.get("end")):
        bao(f"CHAT A trên {ten} (model {model})…")
        a = None
        if ra.get("chat_a") and ra.get("dan_bai"):
            # 27/10: viết tiếp bài dở — mở lại ĐÚNG chat A (Gemini còn nhớ dàn ý A, ADN, các phần đã viết)
            try:
                a = G.PhienChat(ten, cong, model=model, url=ra["chat_a"])
                bao("[1] Mở lại chat A đã có — viết tiếp từ bước còn thiếu…")
            except Exception as e:                           # noqa: BLE001
                bao(f"  ! không mở lại được chat A ({str(e)[:80]}) — mở chat mới với dàn ý đã lưu")
        mo_dau = []                                          # ngữ cảnh gắn vào tin nhắn ĐẦU TIÊN gửi trong chat A này

        def dan_y_a():
            return (f"Mình đang viết kịch bản video YouTube «{tieu_de}» cho kênh «{kenh}». Dưới đây là DÀN Ý A của "
                    f"video:\n{ra['dan_bai'].strip()}")
        if a is None and ra.get("dan_bai"):
            dan = doi_thu.doc_dan_bai(ra["dan_bai"], tieu_de, tong_tu or 1500)
            bao(f"[1] Dàn ý có sẵn ({dan['so_phan']} phần) — gửi kèm lệnh viết đầu tiên làm DÀN Ý A…")
            a = G.PhienChat(ten, cong, model=model)
            mo_dau.append(dan_y_a())
            ra["da_adn"] = False
        elif a is None:
            if ra.get("phan_truoc"):
                _, so_phan, so_tu_chuan, _ = doi_thu.cau_lenh_dan_bai(tieu_de, plugin, tong_tu, y_tuong)
                bao(f"[1] Lập DÀN Ý A cho PHẦN {ra['phan_so']} ({so_phan} phần) — phát triển tiếp các phần trước…")
                lenh = _dien(mau["dan_bai_phan_tiep"], tieu_de=tieu_de, kenh=kenh, phan_so=ra["phan_so"], so_phan=so_phan,
                             tong_tu=so_tu_chuan, phan_truoc=ra["phan_truoc"])
            elif transcript.strip():
                _, so_phan, so_tu_chuan, _ = doi_thu.cau_lenh_dan_bai(tieu_de or "Viết lại video", plugin, tong_tu, y_tuong)
                bao(f"[1] Lập DÀN Ý A {so_phan} phần từ transcript gốc…")
                lenh = _dien(mau["dan_bai_transcript"], so_phan=so_phan, tong_tu=so_tu_chuan, kenh=kenh,
                             transcript=transcript.strip())
            else:
                prompt, so_phan, so_tu_chuan, _ = doi_thu.cau_lenh_dan_bai(tieu_de, plugin, tong_tu, y_tuong)
                bao(f"[1] Lập DÀN Ý A {so_phan} phần theo ADN «{kenh}»…")
                lenh = "Gọi dàn bài sau đây là DÀN Ý A.\n\n" + prompt
            a, kq = _mo_chat_a(G, ten, cong, model, lenh, lambda kq: _dung_dinh_dang(kq, so_phan), bao)
            ra["dan_bai"] = doi_thu.doc_dan_bai(kq, tieu_de, so_tu_chuan)["dan_bai_text"]
            ra["da_adn"] = False

        def ghi():
            ra["chat_a"] = a.url or ra.get("chat_a") or ""
            luu()
        ghi()
        try:
            phan = doi_thu.doc_dan_bai(ra["dan_bai"], tieu_de, tong_tu or 1500)["danh_sach_phan"]
            if not phan:
                raise RuntimeError("không tách được các phần của dàn ý A")
            n = len(phan)
            so_tu = lambda k: so_tu_phan_1 if k == 0 else so_tu_phan               # noqa: E731
            if not ra.get("da_adn"):
                mo_dau.append(nen_adn)

            def gui_a(lenh, toi_thieu=0):
                """Gửi trong chat A. Tin đầu tiên của chat mang theo mo_dau (dàn ý A, phong cách kênh); hỏng / bị từ chối
                -> mở chat MỚI gửi lại cả khối (26/10 đo: chat đã từ chối thì gửi lại trong chat đó vẫn từ chối)."""
                nonlocal a
                if not mo_dau:
                    return _gui(a, lenh, bao, toi_thieu=toi_thieu)
                for lan in range(3):
                    try:
                        kq = _gui(a, "\n\n".join(mo_dau) + "\n\n" + lenh, bao, so_lan=0, toi_thieu=toi_thieu)
                        mo_dau.clear()
                        ra["da_adn"] = True
                        return kq
                    except (TimeoutError, RuntimeError, OSError, ValueError) as e:
                        if lan == 2 or dung():
                            raise
                        bao(f"  ↻ chat A lần {lan + 1}: {str(e)[:80]} — mở chat MỚI gửi lại…")
                        a.dong()
                        a = G.PhienChat(ten, cong, model=model)
                        if dan_y_a() not in mo_dau:              # chat mới chưa biết dàn ý A (Gemini lập ở chat cũ)
                            mo_dau.insert(0, dan_y_a())
            for k in range(len(ra["ban_goc"]), n):
                kiem_dung()
                bao(f"[2] Viết bài gốc phần {k + 1}/{n}: {phan[k]['tieu_de'][:60]}…")
                ra["ban_goc"].append(_sach(gui_a(nhac + _dien(mau["viet_goc"], i=k + 1, ten_phan=phan[k]["tieu_de"],
                                                             so_tu=so_tu(k)), toi_thieu=int(so_tu(k) * 0.4))))
                ghi()
            for k in range(len(ra["sau_sac"]), n):
                kiem_dung()
                bao(f"[3] Viết lại phần {k + 1}/{n} sâu sắc hơn ({so_tu(k)} từ)…")
                lenh = _dien(mau["sau_sac_phan_1" if k == 0 else "sau_sac"], i=k + 1, so_tu=so_tu(k), nguon_du_kien=nguon)
                ra["sau_sac"].append(_sach(gui_a(nhac + lenh + "\n\nBÀI GỐC PHẦN " + str(k + 1) + ":\n" + ra["ban_goc"][k],
                                                 toi_thieu=int(so_tu(k) * 0.4))))
                ghi()
            if not ra.get("end"):
                kiem_dung()
                bao("[4] Viết phần End (theo cách kết bài của kênh)…")
                ket = (f"Theo CÁCH KẾT BÀI của kênh: {kb_kenh['ket_bai']}\n" if kb_kenh.get("ket_bai") else "")
                ra["end"] = _sach(gui_a(DAN_END_HOOK + nhac + ket + mau["end"], toi_thieu=35))
                ghi()
            if not ra.get("hook"):
                kiem_dung()
                bao("[5] Viết phần Hook (theo công thức hook của kênh)…")
                mo = (f"Theo CÔNG THỨC MỞ ĐẦU (hook) của kênh: {kb_kenh['hook_cong_thuc']}\n" if kb_kenh.get("hook_cong_thuc") else "")
                ra["hook"] = _sach(gui_a(DAN_END_HOOK + nhac + mo + mau["hook"], toi_thieu=30))
                ghi()
        finally:
            ra["chat_a"] = a.url or ra.get("chat_a") or ""
            a.dong()

    # ---------------- CHAT B (chat MỚI): viết lại chi tiết, dễ hiểu — hook + phần 1, phần 2…, phần cuối + end
    kiem_dung()
    khuc = [ra["hook"] + "\n\n" + ra["sau_sac"][0]] + ra["sau_sac"][1:]
    khuc[-1] += "\n\n" + ra["end"]
    if len(ra["viet_lai"]) < len(khuc):
        bao(f"CHAT B — viết lại chi tiết, dễ hiểu {len(khuc)} khúc (còn {len(khuc) - len(ra['viet_lai'])})…")
        # 26/10 user: "chat mà viết dễ hiểu thì không cần thêm ADN vào" — chat B chỉ có câu lệnh viết lại + từng khúc
        b = None
        if ra.get("chat_b") and ra["viet_lai"]:
            try:
                b = G.PhienChat(ten, cong, model=model, url=ra["chat_b"])
            except Exception as e:                           # noqa: BLE001
                bao(f"  ! không mở lại được chat B ({str(e)[:80]}) — mở chat mới")
        b = b or G.PhienChat(ten, cong, model=model)
        try:
            for k in range(len(ra["viet_lai"]), len(khuc)):
                kiem_dung()
                bao(f"[6] Viết lại khúc {k + 1}/{len(khuc)}…")
                lenh, toi = mau["viet_lai"] + "\n\n" + khuc[k], max(30, int(len(khuc[k].split()) * 0.4))
                for lan in range(3):
                    try:
                        kq = _gui(b, lenh, bao, so_lan=0 if not ra["viet_lai"] else 2, toi_thieu=toi)
                        break
                    except (TimeoutError, RuntimeError, OSError, ValueError) as e:
                        # 27/10 chạy thật: tin ĐẦU của chat B bị từ chối, nhắc 2 lần vẫn từ chối -> chat đó hỏng, như chat
                        # A: mở chat B MỚI gửi lại (khúc sau đã có bài trong chat thì để _gui mở lại theo ID như cũ)
                        if ra["viet_lai"] or lan == 2 or dung():
                            raise
                        bao(f"  ↻ chat B lần {lan + 1}: {str(e)[:80]} — mở chat MỚI gửi lại…")
                        b.dong()
                        b = G.PhienChat(ten, cong, model=model)
                ra["viet_lai"].append(_sach(kq))
                ra["chat_b"] = b.url or ra.get("chat_b") or ""
                luu()
        finally:
            ra["chat_b"] = b.url or ra.get("chat_b") or ""
            b.dong()
    ra["kich_ban"] = "\n\n".join(ra["viet_lai"])
    ra["giay"] = round(time.time() - t0)
    so_tu_cuoi = len(ra["kich_ban"].split())
    bao(f"✔ Xong quy trình: {so_tu_cuoi} từ, {ra['giay'] // 60} phút {ra['giay'] % 60} giây — đã lưu vào {_thu_muc(ra['ma'])}")
    log(f"[quy trình viết] {tieu_de}: {so_tu_cuoi} từ trên {ten}")
