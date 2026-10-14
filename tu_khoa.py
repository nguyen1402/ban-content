# -*- coding: utf-8 -*-
"""Từ khoá tìm nguồn cho TỪNG CẢNH (hỏi ChatGPT). Người dùng tự tìm hình, video VÀ bản đồ theo từ khoá
(không dựng bản đồ/biểu đồ Remotion nữa — user bỏ 11/10). Mỗi cảnh có:
  noi_dung   nội dung chính nên chiếu (tiếng Việt)
  video      cụm tìm video tiếng Anh (cụ thể -> chung)      video_vi  cụm tìm tiếng Việt
  anh        từ khoá tìm ảnh (tên riêng/vật cụ thể trước)
  dia_diem   địa điểm được nhắc -> từ khoá tìm bản đồ + link Google Maps"""
import hashlib
import json
import os
import shutil
import subprocess

from common import doc_json, duong_cache, ghi_json, hoi_nhieu, log, rut_json

PHIEN_BAN = 3                     # đổi khuôn câu trả lời -> cache cũ coi như chưa có, hỏi lại
_P = """You help a Vietnamese documentary editor find stock footage. For EACH numbered scene of narration below give search keywords so the editor can find matching footage and images by hand on YouTube / Google Images, plus the places to look up on a map.
Story summary: {tom_tat}
Correct names (the narration came from speech recognition, use these spellings): {ten}

For each scene return:
- "noi_dung": ONE short Vietnamese sentence: what the viewer should SEE during this scene (concrete, filmable).
- "video": 3-5 English YouTube search phrases, most specific first (use the proper names of animals, places, organisations, objects that the scene mentions), then more general ones. 2-7 words each.
- "video_vi": 1-2 Vietnamese search phrases.
- "anh": 2-4 short English image-search terms for still photos (named things first: species, person, organisation logo, object, sign).
- "dia_diem": EVERY real geographic place the scene explicitly mentions (country, region, island, city, river, park...), each {{"vi": the words as written in the narration, "en": the place's English name WITH its country for map lookup (e.g. "Palm Island, Queensland, Australia"), "rong_km": width of the map view in km (5-20 for an island or town, 50-300 for a region, 800-4000 for a country)}}. Use [] if no place is mentioned. Do not invent places that are not in the narration.

Return ONLY a JSON array: [{{"id": <scene id>, "noi_dung": "...", "video": ["..."], "video_vi": ["..."], "anh": ["..."], "dia_diem": [{{"vi": "...", "en": "...", "rong_km": 20}}]}}]

SCENES:
{canh}"""


def _sach(x):
    """Danh sách chuỗi không rỗng."""
    return [str(s).strip() for s in (x if isinstance(x, list) else []) if str(s).strip()]


def _bieu_do(x):
    """Dữ liệu biểu đồ hợp lệ (>=2 điểm số) hoặc None."""
    if not isinstance(x, dict):
        return None
    diem = []
    for d in x.get("diem") or []:
        if not isinstance(d, dict):
            continue
        try:
            v = float(str(d.get("gia_tri")).replace(",", "").replace(" ", ""))
        except (TypeError, ValueError):
            continue
        diem.append({"nam": str(d.get("nam", "")).strip()[:14], "gia_tri": v,
                     "_dv": str(d.get("don_vi") or x.get("don_vi") or "").strip().lower()})
    if len(diem) < 2 or len({d.pop("_dv") for d in diem}) > 1:    # khác đơn vị (vd 300 con dê vs 400 ha) -> không vẽ
        return None
    return {"tieu_de": str(x.get("tieu_de", "")).strip()[:60], "don_vi": str(x.get("don_vi", "")).strip()[:30],
            "diem": diem[:8]}


def lam_tu_khoa(canh, ctx, cache, lo=8):
    """Điền c['tu_khoa'] cho mọi cảnh (cache theo id cảnh + nội dung lời, chạy song song mỗi cookie một luồng)."""
    da = doc_json(cache, {}) or {}
    khoa = lambda c: hashlib.md5(c["text"].encode("utf-8")).hexdigest()[:10]      # đổi lời cảnh thì hỏi lại
    can = [c for c in canh if (da.get(str(c["id"])) or {}).get("_k") != khoa(c)
           or (da.get(str(c["id"])) or {}).get("_v") != PHIEN_BAN]
    for vong in range(3):                                   # lô hỏng (trả không phải JSON, thiếu cảnh) -> hỏi lại lô nhỏ hơn
        if not can:
            break
        co_lo = lo if vong == 0 else max(2, lo // (2 * vong))
        lots = [can[i:i + co_lo] for i in range(0, len(can), co_lo)]
        ps = [_P.format(tom_tat=ctx.get("tom_tat", ""), ten=ctx.get("ten", {}),
                        canh=chr(10).join(f"{c['id']}. {c['text']}" for c in lot)) for lot in lots]
        log(f"  từ khoá tìm nguồn{' (hỏi lại lần ' + str(vong) + ')' if vong else ''}: {len(can)} cảnh, "
            f"{len(lots)} lô, mỗi cookie một luồng…")

        def xu_ly(i, tra, lots=lots):
            kq = rut_json(tra)
            if not isinstance(kq, list):
                log(f"    ! lô cảnh {lots[i][0]['id']}-{lots[i][-1]['id']}: trả lời không đọc được "
                    f"({(tra or '')[:80]!r})")
                return
            mp = {}
            for x in kq:
                if isinstance(x, dict):
                    try:
                        mp[int(x.get("id", -1))] = x
                    except (TypeError, ValueError):
                        pass
            for c in lots[i]:
                x = mp.get(c["id"])
                if not x:
                    continue
                dd = []
                for d in x.get("dia_diem") or []:
                    if isinstance(d, dict) and str(d.get("en", "")).strip():
                        try:
                            rk = float(d.get("rong_km") or 20)
                        except (TypeError, ValueError):
                            rk = 20.0
                        dd.append({"vi": str(d.get("vi", "")).strip(), "en": str(d["en"]).strip(),
                                   "rong_km": max(5.0, min(4000.0, rk))})
                da[str(c["id"])] = {"_k": khoa(c), "_v": PHIEN_BAN, "noi_dung": str(x.get("noi_dung", "")).strip(),
                                    "video": _sach(x.get("video"))[:5], "video_vi": _sach(x.get("video_vi"))[:2],
                                    "anh": _sach(x.get("anh"))[:4], "dia_diem": dd[:4],
                                    "bieu_do": _bieu_do(x.get("bieu_do"))}
            ghi_json(cache, da)
        hoi_nhieu(ps, timeout=200, on_xong=xu_ly)
        can = [c for c in can if (da.get(str(c["id"])) or {}).get("_k") != khoa(c)
               or (da.get(str(c["id"])) or {}).get("_v") != PHIEN_BAN]
    for c in can:
        log(f"    ! cảnh {c['id']}: ChatGPT không trả từ khoá sau 3 lượt")
    for c in canh:
        c["tu_khoa"] = da.get(str(c["id"])) or {"noi_dung": "", "video": [], "video_vi": [], "anh": [],
                                                "dia_diem": [], "bieu_do": None}
    log(f"    từ khoá: {sum(1 for c in canh if c['tu_khoa'].get('video'))}/{len(canh)} cảnh; "
        f"cảnh có địa điểm: {sum(1 for c in canh if c['tu_khoa'].get('dia_diem'))}")
    return canh


def _props_ban_do(c, tim_toa):
    dd = (c.get("tu_khoa") or {}).get("dia_diem") or []
    chinh = None
    for d in dd:                                                # tâm = địa điểm đầu tiên tra được toạ độ
        t = tim_toa(d["en"])
        if t:
            chinh = (d, t)
            break
    if not chinh:
        if dd:
            log(f"    ! cảnh {c['id']}: không tra được toạ độ {', '.join(d['en'] for d in dd)}")
        return None
    d0, (lat, lon) = chinh
    dau = []
    for d in dd:
        if d is d0:
            continue
        t = tim_toa(d["en"])
        if t:
            dau.append({"ten": d["en"].split(",")[0], "lat": t[0], "lon": t[1]})
    return {"dia_diem": d0["en"].split(",")[0], "lat": lat, "lon": lon, "rong_km": d0["rong_km"],
            "nam_tu": None, "nam_den": None, "dau": dau[:3], "chu_thich": []}


def chuan_bi_do_hoa(canh):
    """c['do_hoa_phan'] = [{kieu, props, bd, dai}]: bản đồ cho cảnh có địa điểm, biểu đồ cho cảnh có số liệu.
    Cảnh có CẢ hai: bản đồ ~45% đầu cảnh, biểu đồ phần còn lại (theo thứ tự lời thường nói nơi chốn trước, số sau)."""
    import do_hoa
    toa_cache = duong_cache("toa_do.json")
    toa = doc_json(toa_cache, {}) or {}

    def tim_toa(ten):
        if ten not in toa:
            ng = do_hoa._nominatim(ten)                       # noqa: SLF001
            toa[ten] = list(ng) if ng else None
            ghi_json(toa_cache, toa)
        return toa[ten]

    n_bd = n_bi = 0
    for c in canh:
        c.pop("do_hoa", None)
        bd = _props_ban_do(c, tim_toa)
        bi = (c.get("tu_khoa") or {}).get("bieu_do")
        phan = []
        if bd and bi:
            d1 = max(2.5, round(c["dai"] * 0.45, 2))
            if c["dai"] - d1 >= 2.0:
                phan = [{"kieu": "ban_do", "props": bd, "bd": 0.0, "dai": d1},
                        {"kieu": "bieu_do", "props": bi, "bd": d1, "dai": round(c["dai"] - d1, 2)}]
            else:
                phan = [{"kieu": "ban_do", "props": bd, "bd": 0.0, "dai": c["dai"]}]
        elif bd:
            phan = [{"kieu": "ban_do", "props": bd, "bd": 0.0, "dai": c["dai"]}]
        elif bi:
            phan = [{"kieu": "bieu_do", "props": bi, "bd": 0.0, "dai": c["dai"]}]
        c["do_hoa_phan"] = phan
        n_bd += sum(1 for p in phan if p["kieu"] == "ban_do")
        n_bi += sum(1 for p in phan if p["kieu"] == "bieu_do")
    log(f"[3] đồ hoạ Remotion: {n_bd} bản đồ, {n_bi} biểu đồ")
    return canh


def dung_do_hoa(canh, out):
    """Render mọi phần đồ hoạ (bỏ qua phần đã dựng đúng dữ liệu) rồi chép sang ra/<dự án>/do_hoa/."""
    import do_hoa
    import nen_ban_do
    viec, ds = [], []
    for c in canh:
        for k, p in enumerate(c.get("do_hoa_phan") or []):
            clip = duong_cache("clip", f"{c['id']:04d}_dh{k}.mp4")
            h = hashlib.md5(json.dumps([p["kieu"], p["props"], round(p["dai"], 2)], sort_keys=True)
                            .encode()).hexdigest()[:10]
            dau_hieu = clip + ".h"
            cu = ""
            if os.path.isfile(dau_hieu):
                with open(dau_hieu, encoding="utf-8") as f:
                    cu = f.read()
            ds.append((c, k, p, clip))
            if os.path.isfile(clip) and os.path.getsize(clip) > 5000 and cu == h:
                continue
            if p["kieu"] == "ban_do":
                try:
                    pr = nen_ban_do.chuan_bi(p["props"])      # nền OSM thật + đường viền + camera phóng dần
                except Exception as e:                       # noqa: BLE001
                    log(f"    ! nền bản đồ lỗi ({str(e)[:80]}) — dùng bản đồ vector")
                    pr = p["props"]
                comp = "BanDoNen" if pr.get("lop") else "BanDo"
                viec.append({"comp": comp, "giay": p["dai"], "out": clip, "props": pr if pr.get("lop") else p["props"]})
            else:
                viec.append({"comp": "BieuDo", "giay": p["dai"], "out": clip, "props": p["props"]})
            with open(dau_hieu, "w", encoding="utf-8") as f:
                f.write(h)
    if viec:
        log(f"    Remotion dựng {len(viec)} clip đồ hoạ…")
        jobs = duong_cache("do_hoa_jobs", "jobs_moi.json")
        ghi_json(jobs, viec)
        env = dict(os.environ)
        ch = do_hoa._chrome()                                   # noqa: SLF001
        if ch:
            env["BROWSER_EXE"] = ch
        r = subprocess.run(["node", "render.mjs", jobs], cwd=do_hoa.REMOTION, env=env, capture_output=True,
                           timeout=3600, creationflags=0x08000000 if os.name == "nt" else 0)
        log("    " + "\n    ".join(r.stdout.decode("utf-8", "ignore").strip().splitlines()[-3:]))
    thu = os.path.join(out, "do_hoa")
    os.makedirs(thu, exist_ok=True)
    for f in os.listdir(thu):                                   # bỏ đồ hoạ cũ không còn dùng
        if f.endswith(".mp4"):
            os.remove(os.path.join(thu, f))
    for c in canh:
        c["do_hoa_clip"] = []
    for c, k, p, clip in ds:
        if os.path.isfile(clip) and os.path.getsize(clip) > 5000:
            dich = os.path.join(thu, f"canh_{c['id']:04d}_{p['kieu']}.mp4")
            shutil.copyfile(clip, dich)
            c["do_hoa_clip"].append({"kieu": p["kieu"], "file": dich, "bd": p["bd"], "dai": p["dai"]})
        else:
            log(f"    ! cảnh {c['id']}: dựng {p['kieu']} hỏng")
    return canh


def _giay(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def tim_ban_do(d):
    """Từ khoá tìm bản đồ cho một địa điểm: tiếng Anh (tên đầy đủ có nước) + tiếng Việt, kèm link Google Maps."""
    import urllib.parse
    en = d.get("en", "").strip()
    vi = d.get("vi", "").strip()
    ds = [f"{en} map"] if en else []
    ten_vi = vi if len(vi.split()) >= 2 else (en.split(",")[0].strip() or vi)     # "đảo" chung chung -> dùng tên riêng
    if ten_vi:
        ds.append(f"bản đồ {ten_vi}")
    return {"ten": vi or en, "tu_khoa": ds,
            "google_maps": "https://www.google.com/maps/search/" + urllib.parse.quote(en or vi)}


def xuat(canh, out):
    """tu_khoa.json (cho giao diện) + tu_khoa.md (đọc/in) trong ra/<dự án>/."""
    ds = []
    for c in canh:
        k = c.get("tu_khoa") or {}
        ds.append({"id": c["id"], "bat_dau": round(c.get("bat_dau", 0.0), 2), "dai": round(c.get("dai", 0.0), 2),
                   "text": c["text"], "noi_dung": k.get("noi_dung", ""), "video": k.get("video", []),
                   "video_vi": k.get("video_vi", []), "anh": k.get("anh", []),
                   "ban_do": [tim_ban_do(d) for d in k.get("dia_diem", [])]})
        if c.get("nghi_sau"):
            ds[-1]["nghi_sau"] = c["nghi_sau"]                  # quãng lặng chèn (giây) ở CUỐI cảnh
    ghi_json(os.path.join(out, "tu_khoa.json"), ds)
    with open(os.path.join(out, "tu_khoa.md"), "w", encoding="utf-8") as f:
        f.write("# Từ khoá tìm nguồn theo cảnh\n\n")
        for x in ds:
            f.write(f"## Cảnh {x['id']} · {_giay(x['bat_dau'])} → {_giay(x['bat_dau'] + x['dai'])}\n\n")
            f.write(f"> {x['text']}\n\n")
            if x["noi_dung"]:
                f.write(f"- **Nên chiếu:** {x['noi_dung']}\n")
            if x["video"]:
                f.write(f"- **Tìm video:** {' · '.join(x['video'])}\n")
            if x["video_vi"]:
                f.write(f"- **Tìm tiếng Việt:** {' · '.join(x['video_vi'])}\n")
            if x["anh"]:
                f.write(f"- **Tìm ảnh:** {' · '.join(x['anh'])}\n")
            for b in x["ban_do"]:
                f.write(f"- **Tìm bản đồ ({b['ten']}):** {' · '.join(b['tu_khoa'])} · [Google Maps]({b['google_maps']})\n")
            f.write("\n")
    return ds
