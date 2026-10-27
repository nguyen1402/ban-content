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
import time

from common import CACHE_CHUNG, doc_json, ghi_json, log

MAU_FILE = os.path.join(CACHE_CHUNG, "mau_quy_trinh.json")
# 26/10 chạy thật: câu lệnh End / Hook không nhắc tới bài đang viết -> Gemini trả câu lỗi / từ chối; thêm câu dẫn phía trước
DAN_END_HOOK = "Dựa trên toàn bộ bài đã viết lại ở trên:\n"

_KHONG_LAP = (" Đặc biệt, không được viết lặp lại từ, không được lặp lại câu hay cấu trúc lặp, nói chung không được lặp "
              "những từ ngữ giống nhau quá nhiều mà thay thế bằng những cách diễn đạt đa dạng hơn để tránh nhàm chán cho "
              "khán giả.\n LƯU Ý, không lặp lại các từ ngữ có 2 đến 3 từ liên tục trong 1 đoạn, hoặc 1 phần quá 2 lần.\n"
              " Không viết trong canvas, tắt canvas. Trả lời rồi dừng lại.")
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
    "nen_adn": ("ADN KỊCH BẢN CỦA KÊNH «{kenh}» — đây là NỀN TẢNG cho mọi phần viết trong cuộc trò chuyện này:\n{adn}\n\n"
                "Mọi đoạn bạn viết từ giờ phải đúng ngôi kể, giọng văn, nhịp câu và kỹ thuật giữ chân của ADN trên. Các câu "
                "lệnh tôi gửi tiếp theo chỉ BỔ SUNG cho ADN này (độ dài, số đoạn, cách viết số, kêu gọi đăng ký…), không "
                "thay thế giọng của kênh. Chỉ trả lời: Đã nhận ADN."),
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
                 "sang km, acres sang hecta). Không viết trong canvas, tắt canvas. Không được dùng Icon hay biểu tượng như "
                 "(-,*). Không sử dụng dấu hai chấm \":\", dấu ngoặc đơn () hoặc ngoặc kép\"\", vì sẽ sử dụng AI để đọc:"),
    "nguon_transcript": "Chỉ lấy thông tin có trong transcript gốc, KHÔNG BỔ SUNG DỮ KIỆN NGOÀI",
    "nguon_dan_bai": "Chỉ lấy thông tin có trong dàn ý A và bài gốc, KHÔNG BỔ SUNG DỮ KIỆN NGOÀI",
}
TEN_MAU = {"nen_adn": "Nền ADN kênh (gửi sau dàn ý A, chat A)",
           "nhac_adn": "Câu nhắc ADN đứng trước mỗi câu lệnh viết","dan_bai_transcript": "Lập dàn ý A từ transcript (chế độ viết lại)", "viet_goc": "Viết bài gốc từng phần",
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


def chay(tieu_de, plugin, dan_bai_text="", transcript="", tong_tu=None, so_tu_phan_1=300, so_tu_phan=500,
         y_tuong=None, bao=None, dung=lambda: False, model="flash"):
    """Chạy trọn quy trình -> {kich_ban, dan_bai, ban_goc[], sau_sac[], end, hook, viet_lai[], ho_so, giay}."""
    import doi_thu
    import gemini_chrome as G
    bao = bao or (lambda *_: None)
    mau = doc_mau()
    t0 = time.time()
    bao("Tìm tài khoản Gemini PRO…")
    hs = G.ho_so_pro(bao=bao)
    if not hs:
        raise RuntimeError("không có hồ sơ Chrome nào là tài khoản Gemini PRO / Ultra (quy trình viết chỉ chạy trên Pro)")
    ten, cong = hs
    kenh = (plugin or {}).get("kenh_ten") or "kênh"
    nguon = mau["nguon_transcript"] if str(transcript or "").strip() else mau["nguon_dan_bai"]
    kb_kenh = (plugin or {}).get("kich_ban") or {}
    nen_adn = _dien(mau["nen_adn"], kenh=kenh, adn=doi_thu._phong_cach_viet(plugin or {}))   # noqa: SLF001
    nhac = _dien(mau["nhac_adn"], kenh=kenh) + "\n"
    ra = {"ho_so": ten, "dan_bai": "", "ban_goc": [], "sau_sac": [], "end": "", "hook": "", "viet_lai": []}

    def kiem_dung():
        if dung():
            raise RuntimeError("đã dừng theo yêu cầu")

    # ---------------- CHAT A: dàn ý A -> bài gốc -> sâu sắc -> end -> hook (cùng một cuộc chat)
    bao(f"CHAT A trên {ten} (model {model})…")
    if str(dan_bai_text or "").strip():
        so_tu_tong = int(tong_tu or 0) or None
        dan_bai = doi_thu.doc_dan_bai(dan_bai_text, tieu_de, so_tu_tong or 1500)
        bao(f"[1] Đưa dàn ý có sẵn ({dan_bai['so_phan']} phần) vào chat làm DÀN Ý A…")
        a, _ = _mo_chat_a(G, ten, cong, model, "Đây là DÀN Ý A cho video «" + str(tieu_de) + "». Hãy ghi nhớ dàn ý này "
                          "để viết các phần sau. Chỉ trả lời: Đã nhận dàn ý A.\n\n" + dan_bai_text.strip(),
                          lambda kq: bool(kq.strip()), bao)
    else:
        if str(transcript or "").strip():
            _, so_phan, so_tu_chuan, _ = doi_thu.cau_lenh_dan_bai(tieu_de or "Viết lại video", plugin, tong_tu, y_tuong)
            bao(f"[1] Lập DÀN Ý A {so_phan} phần từ transcript gốc…")
            lenh = _dien(mau["dan_bai_transcript"], so_phan=so_phan, tong_tu=so_tu_chuan, kenh=kenh,
                         transcript=str(transcript).strip())
        else:
            prompt, so_phan, so_tu_chuan, _ = doi_thu.cau_lenh_dan_bai(tieu_de, plugin, tong_tu, y_tuong)
            bao(f"[1] Lập DÀN Ý A {so_phan} phần theo ADN «{kenh}»…")
            lenh = "Gọi dàn bài sau đây là DÀN Ý A.\n\n" + prompt
        a, kq = _mo_chat_a(G, ten, cong, model, lenh, lambda kq: _dung_dinh_dang(kq, so_phan), bao)
        dan_bai = doi_thu.doc_dan_bai(kq, tieu_de, so_tu_chuan)
    try:
        ra["dan_bai"] = dan_bai["dan_bai_text"]
        phan = dan_bai["danh_sach_phan"]
        if not phan:
            raise RuntimeError("không tách được các phần của dàn ý A")
        n = len(phan)
        so_tu = lambda k: so_tu_phan_1 if k == 0 else so_tu_phan               # noqa: E731

        kiem_dung()
        bao(f"[1b] Đưa ADN giọng văn kênh «{kenh}» vào chat làm nền cho mọi phần viết…")
        _gui(a, nen_adn, bao)
        for k, p in enumerate(phan):
            kiem_dung()
            bao(f"[2] Viết bài gốc phần {k + 1}/{n}: {p['tieu_de'][:60]}…")
            ra["ban_goc"].append(_sach(_gui(a, nhac + _dien(mau["viet_goc"], i=k + 1, ten_phan=p["tieu_de"], so_tu=so_tu(k)),
                                            bao, toi_thieu=int(so_tu(k) * 0.4))))
        for k in range(n):
            kiem_dung()
            bao(f"[3] Viết lại phần {k + 1}/{n} sâu sắc hơn ({so_tu(k)} từ)…")
            lenh = _dien(mau["sau_sac_phan_1" if k == 0 else "sau_sac"], i=k + 1, so_tu=so_tu(k), nguon_du_kien=nguon)
            ra["sau_sac"].append(_sach(_gui(a, nhac + lenh + "\n\nBÀI GỐC PHẦN " + str(k + 1) + ":\n" + ra["ban_goc"][k], bao,
                                            toi_thieu=int(so_tu(k) * 0.4))))
        kiem_dung()
        bao("[4] Viết phần End (theo cách kết bài của kênh)…")
        ket = (f"Theo CÁCH KẾT BÀI của kênh: {kb_kenh['ket_bai']}\n" if kb_kenh.get("ket_bai") else "")
        ra["end"] = _sach(_gui(a, DAN_END_HOOK + nhac + ket + mau["end"], bao, toi_thieu=35))
        kiem_dung()
        bao("[5] Viết phần Hook (theo công thức hook của kênh)…")
        mo = (f"Theo CÔNG THỨC MỞ ĐẦU (hook) của kênh: {kb_kenh['hook_cong_thuc']}\n" if kb_kenh.get("hook_cong_thuc") else "")
        ra["hook"] = _sach(_gui(a, DAN_END_HOOK + nhac + mo + mau["hook"], bao, toi_thieu=30))
    finally:
        ra["chat_a"] = a.url
        a.dong()

    # ---------------- CHAT B (chat MỚI): viết lại chi tiết, dễ hiểu — hook + phần 1, phần 2…, phần cuối + end
    kiem_dung()
    khuc = [ra["hook"] + "\n\n" + ra["sau_sac"][0]] + ra["sau_sac"][1:]
    if len(khuc) == 1:
        khuc[0] += "\n\n" + ra["end"]
    else:
        khuc[-1] += "\n\n" + ra["end"]
    bao(f"CHAT B (chat mới) — viết lại chi tiết, dễ hiểu {len(khuc)} khúc…")
    # 26/10 user: "chat mà viết dễ hiểu thì không cần thêm ADN vào" — chat B chỉ có câu lệnh viết lại + từng khúc
    b = G.PhienChat(ten, cong, model=model)
    try:
        for k, t in enumerate(khuc):
            kiem_dung()
            bao(f"[6] Viết lại khúc {k + 1}/{len(khuc)}…")
            ra["viet_lai"].append(_sach(_gui(b, mau["viet_lai"] + "\n\n" + t, bao,
                                             toi_thieu=max(30, int(len(t.split()) * 0.4)))))
    finally:
        ra["chat_b"] = b.url
        b.dong()
    ra["kich_ban"] = "\n\n".join(ra["viet_lai"])
    ra["giay"] = round(time.time() - t0)
    so_tu_cuoi = len(ra["kich_ban"].split())
    bao(f"✔ Xong quy trình: {so_tu_cuoi} từ, {ra['giay'] // 60} phút {ra['giay'] % 60} giây")
    log(f"[quy trình viết] {tieu_de}: {so_tu_cuoi} từ trên {ten}")
    return ra
