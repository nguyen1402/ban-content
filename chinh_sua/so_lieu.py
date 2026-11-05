# -*- coding: utf-8 -*-
"""05/11 user: "1 số chỗ số liệu bị sai khi dựng remotion … hỏi lại và đảm bảo nó đúng hơn".
So số HIỆN TRÊN HÌNH của cảnh Remotion (SoDem, chữ giữa thẻ, chu=, thông số được in ra) với số TRONG LỜI KỂ (đọc bằng
chữ: "một nghìn tám trăm bảy mươi" = 1870, "bốn mươi nghìn" = 40000, "bảy mươi lăm phần trăm" = 75).
Số trên hình không khớp số nào trong lời -> báo, để AI sửa đúng số."""
import re

_CHU_SO = {"không": 0, "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5, "nhăm": 5,
           "sáu": 6, "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9}
_DON_VI = {"nghìn": 1000, "ngàn": 1000, "triệu": 10 ** 6, "tỷ": 10 ** 9, "tỉ": 10 ** 9}
_LIEN = {"mười", "mươi", "trăm", "linh", "lẻ", "phẩy", "rưỡi", "nửa"}
_SO_TU = set(_CHU_SO) | set(_DON_VI) | _LIEN
# "năm" đứng một mình thường là "năm (year)": chỉ coi là số 5 khi đi với từ số khác hoặc đứng trước danh từ đếm được
_DEM = {"con", "người", "lần", "ngày", "tháng", "năm", "dặm", "km", "ki-lô-mét", "mét", "tấn", "cái", "chiếc", "loài",
        "giờ", "phút", "giây", "tuổi", "hecta", "héc-ta", "mẫu", "đập", "bức", "đợt", "bang", "nước", "thế", "triệu",
        "nghìn", "trăm", "phần", "inch", "feet", "foot", "độ", "bước", "lớp", "tầng", "đô", "đô-la", "usd"}


def _gia_tri(tu):
    """Một dãy từ số -> số (float) | None."""
    if "phẩy" in tu:
        k = tu.index("phẩy")
        a, b = _gia_tri(tu[:k]), tu[k + 1:]
        if a is None or not b:
            return a
        le = "".join(str(_CHU_SO[w]) for w in b if w in _CHU_SO)
        return float(f"{int(a)}.{le}") if le else a
    tong, nhom, cho, co = 0, 0, 0, False
    for w in tu:
        if w == "mươi":
            nhom += (cho or 1) * 10
            cho = 0
        elif w == "mười":
            nhom += 10
        elif w == "trăm":
            nhom += (cho or 1) * 100
            cho = 0
        elif w in ("linh", "lẻ"):
            continue
        elif w == "rưỡi":
            if tong or nhom or cho:
                return (tong + nhom + cho) + 0.5 if not (tong and not nhom and not cho) else tong * 1.5
            continue
        elif w in _DON_VI:
            nhom += cho
            tong += (nhom or 1) * _DON_VI[w]
            nhom, cho = 0, 0
        else:
            cho = _CHU_SO[w]
        co = True
    return float(tong + nhom + cho) if co else None


def so_trong_loi(text):
    """Mọi số trong câu đọc -> {số}. Có cả chữ số viết sẵn trong câu."""
    ra = set()
    for m in re.finditer(r"\d[\d.,]*", text or ""):
        v = _doc_chu_so(m.group(0))
        if v is not None:
            ra.add(v)
    tu = re.findall(r"[\wÀ-ỹ\-]+", (text or "").lower())
    # "một thế kỷ" = 100 năm, "hai thập kỷ" = 20 năm, "nửa thế kỷ" = 50 (hình hay ghi "100 NĂM")
    for k in range(len(tu) - 1):
        he = {"thế": 100, "thập": 10}.get(tu[k]) if tu[k + 1] in ("kỷ", "kỉ") else None
        if not he:
            continue
        truoc = tu[k - 1] if k else ""
        n = 0.5 if truoc == "nửa" else _CHU_SO.get(truoc) or 1
        ra.add(float(n * he))
    i = 0
    while i < len(tu):
        if tu[i] not in _SO_TU or tu[i] in ("phẩy", "rưỡi", "linh", "lẻ"):
            i += 1
            continue
        if i and tu[i - 1] == "phần" and tu[i] == "trăm":                # "phần trăm" không phải số 100
            i += 1
            continue
        if tu[i] == "nửa":
            ra.add(0.5)
            i += 1
            continue
        j = i
        while j < len(tu) and tu[j] in _SO_TU:
            # 15 đọc "mười lăm", 25 "hai mươi lăm": "mười năm" / "hai mươi năm" là 10 / 20 NĂM -> dừng dãy ở "năm"
            if j > i and tu[j] == "năm" and tu[j - 1] in ("mười", "mươi"):
                break
            # hai chữ số liền nhau không có mươi / trăm / nghìn xen giữa = HAI số ("ba năm" = 3 năm, "mười một năm
            # một nghìn…" = tháng 11 năm 1…) -> cắt dãy
            if j > i and tu[j] in _CHU_SO and tu[j - 1] in _CHU_SO and tu[j] not in ("mốt", "tư", "lăm", "nhăm"):
                break
            j += 1
        day = tu[i:j]
        # "năm" (year) đứng đầu dãy mà không đi kèm số -> bỏ chữ "năm" ("những năm một nghìn…")
        while len(day) > 1 and day[0] == "năm" and day[1] in _CHU_SO and day[1] not in ("lăm", "nhăm"):
            day = day[1:]                                                # "năm một nghìn…": năm = year, không phải 5
        if day == ["năm"] and not (j < len(tu) and tu[j] in _DEM):
            i = j
            continue
        if day in (["một"],) and not (j < len(tu) and tu[j] in _DEM | {"đến", "tới", "hay", "hoặc"}):
            i = j
            continue
        if day and not any(w in _CHU_SO or w == "mười" for w in day):
            i = j                                                        # "hàng triệu", "hàng nghìn": không phải số cụ thể
            continue
        v = _gia_tri(day)
        if v is not None:
            if j + 1 < len(tu) and tu[j] == "phần" and tu[j + 1] == "trăm":
                pass                                                     # phần trăm: giữ nguyên số (75 -> 75%)
            ra.add(v)
        i = j
    return ra


def _doc_chu_so(s):
    """'40.000' / '40,000' / '1870' / '2,5' / '1.5' -> số | None (dấu . , theo kiểu Việt / Anh)."""
    s = s.strip(".,")
    if not s:
        return None
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        return float(re.sub(r"[.,]", "", s))
    if re.fullmatch(r"\d+[.,]\d{1,2}", s):
        return float(s.replace(",", "."))
    if re.fullmatch(r"\d+", s):
        return float(s)
    return None


_HE_SO = {"nghìn": 1000, "ngàn": 1000, "k": 1000, "triệu": 10 ** 6, "tr": 10 ** 6, "tỷ": 10 ** 9, "tỉ": 10 ** 9,
          "million": 10 ** 6, "billion": 10 ** 9, "thousand": 1000, "m": 1}


def so_hien(chuoi):
    """Chuỗi hiện trên hình -> [số] ('40.000 con' -> 40000, '3 triệu' -> 3000000, '1870s' -> 1870, '75%' -> 75)."""
    ra = []
    for m in re.finditer(r"(\d[\d.,]*)\s*(triệu|tỷ|tỉ|nghìn|ngàn|million|billion|thousand|k\b|tr\b)?", str(chuoi or ""), re.I):
        v = _doc_chu_so(m.group(1))
        if v is None:
            continue
        if m.group(2):
            v *= _HE_SO[m.group(2).lower()]
        ra.append(v)
    return ra


def _khop(n, loi):
    if n in loi:
        return True
    for m in loi:
        for k in (1000, 10 ** 6, 10 ** 9):
            if abs(n * k - m) < 0.5 or abs(m * k - n) < 0.5:            # "3" + don_vi "triệu" / lời "ba triệu"
                return True
        if m and abs(n - m) / m < 0.005:                                  # làm tròn
            return True
    return False


def _bieu_thuc(expr, code, pr):
    """Giá trị một biểu thức trong JSX (số, 'chuỗi', props.x, tên biến) -> số / chuỗi | None."""
    e = expr.strip().strip("{}").strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", e):
        return float(e)
    m = re.fullmatch(r"(['\"`])(.*)\1", e, re.S)
    if m:
        return m.group(2)
    m = re.fullmatch(r"(?:props\.)?(\w+)(?:\s*(?:\?\?|\|\|)\s*(.+))?", e)
    if not m:
        return None
    ten, mac = m.group(1), m.group(2)
    if ten in pr:
        return pr[ten]
    d = re.search(rf"\b(?:const|let|var)\s+{ten}\s*=\s*([^;\n]+)", code)
    if d and d.group(1).strip() != e:
        return _bieu_thuc(d.group(1), code, pr)
    d = re.search(rf"[{{,]\s*{ten}\s*=\s*([^,}}\n]+)", code)              # mặc định trong tham số ({so = 40000})
    if d:
        return _bieu_thuc(d.group(1), code, pr)
    return _bieu_thuc(mac, code, pr) if mac else None


def so_tren_hinh(code, pr):
    """Các số cảnh in ra màn hình -> [(số, nguồn)]."""
    code = re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", code or "", flags=re.S)
    body = code.split("export const Canh", 1)[-1]
    pr = pr or {}
    ra = []

    def them(gt, nguon):
        if isinstance(gt, (int, float)) and not isinstance(gt, bool):
            ra.append((float(gt), nguon))
        elif isinstance(gt, str):
            for v in so_hien(gt):
                ra.append((v, f"{nguon}: «{gt[:40]}»"))

    for m in re.finditer(r"<SoDem\b([^>]*)>", body):
        a = m.group(1)
        s = re.search(r"\bso\s*=\s*(\{[^}]+\}|\"[^\"]*\"|'[^']*')", a)
        if s:
            gt = _bieu_thuc(s.group(1), code, pr)
            dv = re.search(r"\bdon_vi\s*=\s*(\{[^}]+\}|\"[^\"]*\"|'[^']*')", a)
            dvg = _bieu_thuc(dv.group(1), code, pr) if dv else ""
            if isinstance(gt, (int, float)) and isinstance(dvg, str) and dvg.strip().lower() in _HE_SO:
                gt = gt * _HE_SO[dvg.strip().lower()]
            them(gt, "SoDem")
    for m in re.finditer(r">([^<>{}]*\d[^<>{}]*)<", body):
        t = m.group(1).strip()
        if t and not re.search(r"[=;(){}]|=>", t):
            them(t, "chữ")
    for m in re.finditer(r">\s*\{\s*([\w.]+)\s*\}\s*<", body):
        them(_bieu_thuc(m.group(1), code, pr), "chữ")
    for m in re.finditer(r"<(?:ChuNoi|Nhan)\b[^>]*?\bchu\s*=\s*(\{[^}]+\}|\"[^\"]*\"|'[^']*')", body):
        them(_bieu_thuc(m.group(1), code, pr), "chữ")
    return ra


def kiem(code, pr, loi_cau, loi_quanh=""):
    """-> [(số, nguồn)] số trên hình KHÔNG có trong lời kể (bỏ 0, 1). loi_quanh: lời câu trước / sau (số đó đúng nhưng
    thuộc câu bên cạnh thì không tính là sai)."""
    loi = so_trong_loi(loi_cau) | so_trong_loi(loi_quanh)
    sai, da = [], set()
    for n, nguon in so_tren_hinh(code, pr):
        if n in (0, 1) or n in da or _khop(n, loi):
            continue
        da.add(n)
        sai.append((n, nguon))
    return sai


def dinh_dang(n):
    return f"{int(n):,}".replace(",", ".") if float(n).is_integer() else str(n).replace(".", ",")


# --- đọc chữ THẬT trên khung hình (dựng thử cỡ nhỏ) ---------------------------------------------------------------------
# Đọc code không đủ (bộ đếm tự viết, biểu thức toLocaleString, chuỗi ghép…): bọc cảnh trong một lớp in ra mọi chữ có số
# đang NHÌN THẤY (không ẩn, độ mờ >= 0,15, nằm trong khung), mỗi phần tử lấy chữ ở khung CUỐI nó còn hiện (bộ đếm đã đếm
# xong). SoDem (thư viện) đọc thẳng số đích data-so.
BUOC_DOC = 20                  # khung: đọc mỗi 2/3 giây

_BOC = r"""import React, {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill, Composition, registerRoot, useCurrentFrame} from 'remotion';
import {Canh} from './%(mod)s';
const P = %(props)s;
const Doc = (p) => {
  const f = useCurrentFrame();
  const r = useRef(null);
  useLayoutEffect(() => {
    const root = r.current; if (!root) return;
    const W = root.getBoundingClientRect(), ds = [];
    const thay = (el) => {
      let o = 1;
      for (let e = el; e && e !== root.parentElement; e = e.parentElement) {
        const s = getComputedStyle(e);
        if (s.display === 'none' || s.visibility === 'hidden') return false;
        o *= +s.opacity;
      }
      if (o < 0.15) return false;
      const b = el.getBoundingClientRect();
      const x = b.left - W.left, y = b.top - W.top;                 // khung 1920×1080 (gốc có thể nằm ngoài màn hình)
      return b.width > 0 && b.height > 0 && x + b.width > 0 && x < 1920 && y + b.height > 0 && y < 1080;
    };
    const duong = (el) => { const a = []; for (let e = el; e && e !== root; e = e.parentElement) a.push(e.tagName + ':' + [...(e.parentElement ? e.parentElement.children : [])].indexOf(e)); return a.reverse().join('/'); };
    root.querySelectorAll('[data-so]').forEach((e) => { if (thay(e)) ds.push([duong(e), String(e.dataset.so) + ' ' + (e.dataset.dv || '')]); });
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const gom = new Map();
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      const el = n.parentElement;
      if (!el || el.closest('[data-so]') || !/\d/.test(n.textContent)) continue;
      const k = el.closest('div,text,span,p,h1,h2,h3,tspan') || el;
      if (!thay(k)) continue;
      gom.set(k, (gom.get(k) || '') + n.textContent);
    }
    gom.forEach((t, el) => ds.push([duong(el), t.replace(/\s+/g, ' ').trim()]));
    console.log('CHU ' + JSON.stringify({f, ds}));
  });
  return <AbsoluteFill ref={r}><Canh {...p} /></AbsoluteFill>;
};
registerRoot(() => <Composition id="thu" component={Doc} width={1920} height={1080} fps={30}
  durationInFrames={%(khung)d} defaultProps={P} />);
"""


def chu_hien(ma, props, giay, mod=None):
    """-> ({đường phần tử: chữ cuối cùng hiện}, lỗi). Chỉ chữ có chữ số."""
    import json
    import os
    import subprocess
    import nhan_y_ai as ai
    khung = max(30, round(giay * 30))
    entry = os.path.join(ai.THU_AI, f"_doc_{ma}.jsx")
    with open(entry, "w", encoding="utf-8") as f:
        f.write(_BOC % {"mod": mod or ma + ".jsx", "props": json.dumps(props or {}, ensure_ascii=False), "khung": khung})
    code = open(os.path.join(ai.THU_AI, mod or ma + ".jsx"), encoding="utf-8").read()
    pub = ai._pub_nho(ma, code + json.dumps(props or {}, ensure_ascii=False))     # noqa: SLF001
    tam = os.path.join(ai.CACHE_CHUNG, "nhan_y", "thu_ai", "_doc")
    os.makedirs(tam, exist_ok=True)
    ds_k = sorted(set(list(range(0, khung, BUOC_DOC)) + [khung - 1]))
    env = dict(os.environ)
    try:
        import do_hoa
        if do_hoa._chrome():                                             # noqa: SLF001
            env["BROWSER_EXE"] = do_hoa._chrome()                        # noqa: SLF001
    except Exception:                                                    # noqa: BLE001
        pass
    try:
        r = subprocess.run(["node", "doc_chu.mjs", entry, pub, tam, ",".join(map(str, ds_k))], cwd=ai.REMOTION,
                           capture_output=True, timeout=600, env=env, creationflags=0x08000000 if os.name == "nt" else 0)
    finally:
        try:
            os.remove(entry)
        except OSError:
            pass
    t = (r.stdout or b"").decode("utf-8", "ignore")
    cuoi = {}
    for d in t.splitlines():
        if d.startswith("CHU "):
            try:
                x = json.loads(d[4:])
            except ValueError:
                continue
            for duong, chu in x["ds"]:
                if x["f"] >= cuoi.get(duong, (-1, ""))[0]:
                    cuoi[duong] = (x["f"], chu)
    loi = "" if "XONG" in t else (t + (r.stderr or b"").decode("utf-8", "ignore"))[-600:]
    return {k: v[1] for k, v in cuoi.items()}, loi


def kiem_hinh(ma, props, giay, loi_cau, loi_quanh="", mod=None):
    """Kiểm bằng chữ THẬT trên khung -> ([(số, «chữ»)] sai, lỗi dựng)."""
    chu, loi_d = chu_hien(ma, props, giay, mod)
    loi = so_trong_loi(loi_cau) | so_trong_loi(loi_quanh)
    sai, da = [], set()
    for t in chu.values():
        for n in so_hien(t):
            if n in (0, 1) or n in da or _khop(n, loi):
                continue
            da.add(n)
            sai.append((n, t[:60]))
    return sai, loi_d
