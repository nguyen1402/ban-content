"""29/10 user ("nhiều lúc nó còn nhận nhầm chó với sói"; "cảnh mô tả tấn công thì thằng chấm có chấm được không"):
SigLIP biết "có con giống sói" chứ không phân biệt sói / chó husky, cũng không biết "đang tấn công" hay "đứng yên".
-> CHẤM SO SÁNH trên máy (không gửi Gemini — gửi nhiều thì lỗi):
  1. Đúng con: mảnh mà con DỄ NHẦM (chó, husky, cáo…) thắng chủ thể ở >= TI_LE_NHAM số khung -> bỏ khỏi kho chủ thể đó.
  2. Đúng hành động: câu tấn công / săn / đuổi — đoạn footage mà "đứng yên / nằm / đi chậm" thắng câu hành động -> không dùng.
  3. Lọc tên video trước khi tải: tên có chữ của con dễ nhầm (husky, dog, chó…) mà con đó không phải chủ thể của bài -> bỏ.
Bảng BANG sửa tay được; thêm loài mới: khoá = từ tiếng Anh trong mo_ta_en của chủ thể."""
import re

import numpy as np

# 02/11 user: bảng con vật BANG / DONG_VAT viết tay cho bài sói / cừu (chosoi) -> áp cho chủ đề khác dễ loại oan footage
# (cá mút đá: chim mòng biển trên hồ bị coi là con vật lạ). TẮT; bộ băm Bàn dựng có bộ lọc chung riêng. Bật lại: True.
BAT = False
TI_LE_NHAM = 0.4            # >= bấy nhiêu phần khung con dễ nhầm điểm cao hơn chủ thể -> mảnh là con dễ nhầm
LECH_NHAM = 0.0             # con dễ nhầm phải hơn chủ thể bấy nhiêu điểm (khung) mới tính là nhầm
CO_MAT = 0.05              # khung chỉ tính khi con dễ nhầm thật sự có trong hình (điểm >= mức này; người, đồng cỏ… thì không)

# khoá (từ tiếng Anh trong mô tả chủ thể) -> [(mô tả con dễ nhầm cho SigLIP, [chữ trong tên video để bỏ trước khi tải])]
BANG = {
    "wolf": [("a pet dog", ["dog", "dogs", "puppy", "puppies", "chó", "cún"]),
             ("a husky dog", ["husky", "huskies", "malamute"]),
             ("a german shepherd dog", ["german shepherd", "becgie", "béc giê"]),
             ("a fox", ["fox", "foxes", "cáo"]),
             ("an african wild dog", ["african wild dog", "painted dog", "chó hoang"]),   # 29/10: chosoi lọt vào kho sói
             ("a hyena", ["hyena", "linh cẩu"])],
    "fox": [("a pet dog", ["dog", "dogs", "puppy", "chó"]), ("a cat", ["cat", "cats", "mèo"])],
    "coyote": [("a pet dog", ["dog", "dogs", "puppy", "chó"])],
    "lion": [("a pet cat", ["cat", "kitten", "mèo"]), ("a dog", ["dog", "chó"])],
    "tiger": [("a pet cat", ["cat", "kitten", "mèo"])],
    "leopard": [("a cheetah", ["cheetah", "báo săn"]), ("a pet cat", ["cat", "kitten", "mèo"])],
    "cheetah": [("a leopard", ["leopard", "báo hoa mai"])],
    "sheep": [("a goat", ["goat", "goats", "dê"]), ("a white dog", ["dog", "chó"])],
    "goat": [("a sheep", ["sheep", "cừu"])],
    "crocodile": [("a lizard", ["lizard", "thằn lằn"]), ("a log in the water", [])],
    "alligator": [("a lizard", ["lizard", "thằn lằn"]), ("a log in the water", [])],
    "shark": [("a dolphin", ["dolphin", "cá heo"])],
    "eagle": [("a pigeon", ["pigeon", "bồ câu"]), ("a seagull", ["seagull", "gull", "mòng biển"])],
    "bear": [("a dog", ["dog", "chó"])],
    "horse": [("a donkey", ["donkey", "lừa"])],
    "seal": [("a dog", ["dog", "chó"])],
}

# câu hành động mạnh (tấn công / săn / đuổi): đoạn footage phải giống hành động hơn giống cảnh yên
HANH_DONG_MANH = re.compile(r"tấn công|vồ|cắn|xé|săn|lao (vào|tới|lên)|giết|hạ gục|đuổi|rượt|ngoạm|chiến đấu|đánh nhau|"
                            r"\b(attack|attacking|hunt|hunting|chase|chasing|lunge|lunging|bite|biting|kill|killing|"
                            r"fight|fighting|pounce|pouncing|ambush)\b", re.I)
TINH = ["a {} standing still", "a {} lying down resting", "a {} sitting calmly", "a {} walking slowly", "a close-up portrait of a {}"]


def khoa_cua(mo_ta_en):
    """Từ khoá BANG có trong mô tả chủ thể (vd 'Wild wolf prowling…' -> 'wolf'), không có -> None."""
    s = (mo_ta_en or "").lower()
    return next((k for k in BANG if re.search(_so_nhieu(k), s)), None)


def _so_nhieu(k):
    """29/10: 'wolves' (số nhiều -ves) trước đây không khớp 'wolf' -> chủ thể 'Wild wolves…' bỏ qua mọi kiểm tra."""
    ves = f"|{k[:-1]}ves" if k.endswith("f") else ""
    return rf"\b(?:{k}|{k}s|{k}es{ves})\b"


def kho_nham(vids, mo_ta_cd, log=print):
    """vids: [(kid, t, e, …)] như goi_y._chi_muc; mo_ta_cd: {id chủ thể: mô tả en}.
    -> {id chủ thể: {kid là con dễ nhầm}} (chỉ chủ thể có trong BANG)."""
    if not BAT:
        return {}
    import nhung_siglip
    ra = {}
    khoa_ds = {i: khoa_cua(mt) for i, mt in mo_ta_cd.items()}
    dem = {}
    for k in {k for k in khoa_ds.values() if k}:
        V = nhung_siglip.nhung_chu([f"a photo of a {k}"] + [x for x, _ in BANG[k]])
        bo = set()
        for it in vids:
            e = np.asarray(it[2])
            if not len(e):
                continue
            S = e @ V.T                                      # (khung, 1 + số con dễ nhầm)
            alt = S[:, 1:].max(1)
            if ((alt - S[:, 0] > LECH_NHAM) & (alt >= CO_MAT)).mean() >= TI_LE_NHAM:
                bo.add(it[0])
        dem[k] = len(bo)
        for i, kk in khoa_ds.items():
            if kk == k:
                ra[i] = bo
    if dem:
        log("  dễ nhầm — bỏ mảnh giống con khác hơn chủ thể: " + ", ".join(f"{k} {n}" for k, n in dem.items()))
    return ra


# 29/10 user (chosoi: người tiền sử, chuồng gà trong câu nói về sói / cừu): điểm câu cao chưa chắc có chủ thể trong hình.
# 4. Chủ thể phải CÓ trong hình: câu của chủ thể là con vật trong BANG -> đoạn footage điểm "a photo of a <con>" >= CO_CHU_THE
#    (đo chosoi: sói / cừu thật 0,10-0,15; dải 0,06-0,075 toàn hươu, chó hoang, nhà trại, hàng rào; người da thú 0,05).
# 5. Con vật LẠ: con vật không có trong bài nổi nhất trong hình (>= CON_LA_MUC và hơn mọi con của bài CON_LA_LECH) -> bỏ
#    mảnh ở mọi câu (chuồng gà 0,096 / 0,037; "bò" hay báo nhầm cảnh trang trại có người ~0,07 nên mức cao).
CO_CHU_THE = 0.075
CON_LA_MUC = 0.08
CON_LA_LECH = 0.03
# con vật hay gặp: từ tiếng Anh (dò trong mô tả chủ thể) -> chữ trong tên video để bỏ trước khi tải
DONG_VAT = {
    "wolf": ["wolf", "wolves", "sói"], "sheep": ["sheep", "lamb", "cừu"], "dog": ["dog", "dogs", "puppy", "chó"],
    "chicken": ["chicken", "chickens", "poultry", "hen", "hens", "rooster", "gà"], "cow": ["cow", "cows", "cattle", "bò"],
    "pig": ["pig", "pigs", "hog", "lợn", "heo"], "horse": ["horse", "horses", "ngựa"], "duck": ["duck", "ducks", "vịt"],
    "cat": ["cat", "cats", "kitten", "mèo"], "deer": ["deer", "elk", "hươu", "nai"], "goat": ["goat", "goats", "dê"],
    "llama": ["llama", "alpaca"], "bear": ["bear", "bears", "gấu"], "fox": ["fox", "foxes", "cáo"],
    "bird": ["bird", "birds", "chim"], "fish": ["fish"],                                   # "cá" hay dính "cá nhân"
}
TEN_LA = ["primitive tribe", "caveman", "cavemen", "prehistoric", "tiền sử"]   # cảnh dựng người xưa (thường là AI không nhãn)


def _con_trong_bai(ds_mo_ta_en):
    chu = " ".join(x or "" for x in ds_mo_ta_en).lower()
    return {k for k in DONG_VAT if re.search(_so_nhieu(k), chu)}


def vec_chu(mo_ta_en):
    """Vector "a photo of a <con>" của chủ thể là con vật trong BANG (kiểm tra có trong hình); khác -> None."""
    k = khoa_cua(mo_ta_en)
    if not BAT or not k:
        return None
    if k not in _VEC_CHU:
        import nhung_siglip
        _VEC_CHU[k] = nhung_siglip.nhung_chu([f"a photo of a {k}"])[0]
    return _VEC_CHU[k]


_VEC_CHU = {}


def con_la(vids, ds_mo_ta_en, log=print):
    """Mảnh mà con vật KHÔNG có trong bài nổi nhất trong hình -> {kid} (bỏ ở mọi câu)."""
    if not BAT:
        return set()
    bai = _con_trong_bai(ds_mo_ta_en)
    la = [k for k in DONG_VAT if k not in bai]
    if not bai or not la:
        return set()
    import nhung_siglip
    ds = sorted(bai) + la
    V = nhung_siglip.nhung_chu([f"a photo of a {k}" for k in ds])
    bo, dem = set(), {}
    for it in vids:
        e = np.asarray(it[2])
        if not len(e):
            continue
        S = (e @ V.T).mean(0)
        nb, sl = S[:len(bai)].max(), S[len(bai):]
        j = int(sl.argmax())
        if sl[j] >= CON_LA_MUC and sl[j] - nb >= CON_LA_LECH:
            bo.add(it[0])
            dem[la[j]] = dem.get(la[j], 0) + 1
    if bo:
        log(f"  con vật lạ (không có trong bài: {', '.join(sorted(bai))}) — bỏ {len(bo)} mảnh: "
            + ", ".join(f"{k} {n}" for k, n in sorted(dem.items(), key=lambda x: -x[1])))
    return bo


def vec_tinh(mo_ta_en):
    """Ma trận vector các cảnh YÊN của chủ thể (đứng yên, nằm…) để so với câu hành động; chủ thể ngoài BANG -> None."""
    k = khoa_cua(mo_ta_en)
    if not BAT or not k:
        return None
    import nhung_siglip
    return np.stack([nhung_siglip.vec_mo_ta(x.format(k), []) for x in TINH])


def tu_cam(ds_mo_ta_en):
    """Chữ trong tên video phải bỏ trước khi tải: chữ của con dễ nhầm, trừ khi con đó cũng là chủ thể của bài."""
    if not BAT:
        return []
    chu = " ".join(ds_mo_ta_en).lower()
    cam = []
    for k in {khoa_cua(x) for x in ds_mo_ta_en} - {None}:
        for mo_ta, tu in BANG[k]:
            con = mo_ta.split()[-1]                          # 'a husky dog' -> 'dog'
            if re.search(rf"\b{re.escape(con)}s?\b", chu):
                continue                                     # bài có nói về con đó -> không cấm
            cam += tu
    bai = _con_trong_bai(ds_mo_ta_en)                       # 29/10: con vật không có trong bài + cảnh người xưa
    if bai:
        for k, tu in DONG_VAT.items():
            if k not in bai:
                cam += [w for w in tu if not any(w in DONG_VAT[b_] for b_ in bai)]
        cam += TEN_LA
    return sorted(set(cam))


def ten_bi_cam(tieu_de, cam):
    s = (tieu_de or "").lower()
    return next((w for w in cam if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", s)), None)
