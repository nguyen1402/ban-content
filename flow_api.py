# -*- coding: utf-8 -*-
"""Gửi trực tiếp lệnh batchexecute tới Google Flow (flow.google.com) qua Chrome CDP.
Không bấm nút trên giao diện. Bản Flow boq_labs-ai-sandbox-frontend_20261021.10_p0.

Các RPC hỗ trợ:
  - Video:
    + YhhmEf: Tạo video text-to-video (BatchAsyncGenerateVideoText)
    + jwpduf: Kiểm tra tiến độ tạo video (BatchCheckAsyncVideoGenerationStatus)
    + as29s: Lấy link media video/ảnh (GetMedia -> link flow-content.google/video/...)
  - Ảnh:
    + ogiZ0b: Tạo ảnh (BatchGenerateImages)
    + Zzl0ze: Lấy danh sách nội dung dự án (GetProjectContents)
    + HTrJv: Danh sách model (GetModels)
"""
import json
import os
import re
import time
import urllib.parse
from common import log

SITE_KEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"

MODEL_MAP = {
    # Mã model chuẩn của Flow (đọc từ RPC HTrJv):
    "abra_t2v_4s_360p": {"code": "abra_t2v_4s_360p", "flag": 4, "diem": "4", "ten": "Omni 360p 4s"},
    "abra_t2v_10s_360p": {"code": "abra_t2v_10s_360p", "flag": 4, "diem": "7", "ten": "Omni 360p 10s"},
    "abra_t2v_10s": {"code": "abra_t2v_10s", "flag": 1, "diem": "15", "ten": "Omni 720p 10s"},
    "veo_3_1_t2v_lite": {"code": "veo_3_1_t2v_lite", "flag": 1, "diem": "10", "ten": "Veo 3.1 Lite"},
    "veo_3_1_t2v_fast": {"code": "veo_3_1_t2v_fast", "flag": 1, "diem": "20", "ten": "Veo 3.1 Fast"},
    "veo_3_1_t2v": {"code": "veo_3_1_t2v", "flag": 1, "diem": "100", "ten": "Veo 3.1 Quality"},
    # Tên hiển thị UI:
    "Veo 3.1 - Fast": {"code": "veo_3_1_t2v_fast", "flag": 1, "diem": "20", "ten": "Veo 3.1 Fast"},
    "Veo 3.1 - Lite": {"code": "veo_3_1_t2v_lite", "flag": 1, "diem": "10", "ten": "Veo 3.1 Lite"},
    "Veo 3.1 - Quality": {"code": "veo_3_1_t2v", "flag": 1, "diem": "100", "ten": "Veo 3.1 Quality"},
}

_URL_MEDIA = re.compile(r'https://flow-content\.google/(?:video|image)/([0-9a-zA-Z_-]+)\?(?:[^"\\\s]|\\+u00[0-9a-fA-F]{2})*')


def thoat_url(u):
    """Bỏ escape \\u003d (=) và \\u0026 (&) trong link trả về từ JSON."""
    u = re.sub(r"\\+u003d", "=", u)
    return re.sub(r"\\+u0026", "&", u)


def giai_ma_model(model_name, phan_giai="", do_dai=""):
    """Ánh xạ tên model từ giao diện hoặc mã model về thông tin chuẩn (code, flag, diem, ten)."""
    m = str(model_name or "").strip()
    if m in MODEL_MAP:
        return MODEL_MAP[m]
    m_lower = m.lower()
    if "quality" in m_lower or m == "Veo 3.1 - Quality":
        return MODEL_MAP["veo_3_1_t2v"]
    if "lite" in m_lower or m == "Veo 3.1 - Lite":
        return MODEL_MAP["veo_3_1_t2v_lite"]
    if "fast" in m_lower or m == "Veo 3.1 - Fast":
        return MODEL_MAP["veo_3_1_t2v_fast"]
    if "omni" in m_lower or m == "Omni 1.1 Flash":
        pg = str(phan_giai or "").strip().lower()
        dd = str(do_dai or "").strip().lower()
        if "360" in pg:
            if "4" in dd:
                return MODEL_MAP["abra_t2v_4s_360p"]
            return MODEL_MAP["abra_t2v_10s_360p"]
        return MODEL_MAP["abra_t2v_10s"]
    flag = 4 if "360p" in m else 1
    return {"code": m, "flag": flag, "diem": "?", "ten": m}


# Đoạn JS gốc dùng chung để gọi batchexecute trong ngữ cảnh trang Chrome
_JS_BATCHEXECUTE = r"""
async function __bc_batchexecute(rpc, inner) {
  const bl = window.WIZ_global_data?.cfb2h || '';
  const fsid = window.WIZ_global_data?.FdrFJe || '';
  const at = window.WIZ_global_data?.SNlM0e || '';
  const sourcePath = location.pathname;
  window.__bc_reqid = (window.__bc_reqid || 100000) + 100000;

  const url = `https://flow.google.com/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=${encodeURIComponent(rpc)}&source-path=${encodeURIComponent(sourcePath)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=en&_reqid=${window.__bc_reqid}&rt=c`;
  const reqPayload = [[[rpc, JSON.stringify(inner), null, "generic"]]];
  const body = `f.req=${encodeURIComponent(JSON.stringify(reqPayload))}&at=${encodeURIComponent(at)}&`;

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
      'X-Same-Domain': '1'
    },
    credentials: 'include',
    body: body
  });

  const text = await res.text();
  const clean = text.replace(/^\)\]\}'\s*/, '');
  const lines = clean.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed.startsWith('[[')) continue;
    try {
      const arr = JSON.parse(trimmed);
      for (const item of arr) {
        if (Array.isArray(item) && item[0] === 'wrb.fr' && item[1] === rpc) {
          if (item[5]) {
            return { error: true, errorDetails: item[5], rawText: text };
          }
          const payload = typeof item[2] === 'string' ? JSON.parse(item[2]) : item[2];
          return { error: false, payload: payload, rawText: text };
        }
      }
    } catch(e) {}
  }
  return { error: true, errorDetails: 'cannot_parse_envelope', rawText: text };
}

async function __bc_recaptcha(action) {
  const siteKey = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';
  for (let i = 0; i < 30; i++) {
    if (window.grecaptcha?.enterprise?.execute) break;
    await new Promise(r => setTimeout(r, 200));
  }
  if (!window.grecaptcha?.enterprise?.execute) {
    throw new Error('reCAPTCHA Enterprise chưa sẵn sàng');
  }
  return await window.grecaptcha.enterprise.execute(siteKey, {action: action});
}
"""


def _chay_js(ph, doan_code):
    """Thực thi mã async JavaScript trong Chrome qua CDP Runtime.evaluate."""
    r = ph.ws.goi("Runtime.evaluate", awaitPromise=True, returnByValue=True, expression=doan_code)
    if "exceptionDetails" in r:
        raise RuntimeError(f"Lỗi JS CDP: {r['exceptionDetails']}")
    res = r.get("result", {})
    return res.get("value")


def lay_id_du_an(ph):
    """Lấy ID dự án Flow từ location.pathname (/project/<id>)."""
    return ph.js(r"""(() => {
        const m = location.pathname.match(/\/project\/([^\/?#]+)/);
        return m ? m[1] : '';
    })()""")


def tao_video_batchexecute(ph, prompt, model="veo_3_1_t2v_fast", ti_le="16:9", phan_giai="", do_dai="", so=1):
    """Gửi trực tiếp lệnh tạo video YhhmEf (BatchAsyncGenerateVideoText) qua batchexecute.
    Trả về dict {error, payload, op_ids, rawText}.
    """
    m_info = giai_ma_model(model, phan_giai, do_dai)
    model_code = m_info["code"]
    co_code = m_info["flag"]
    ti_le_code = 1 if "9:16" in str(ti_le) else 2
    so = max(1, min(4, int(so or 1)))

    js = _JS_BATCHEXECUTE + f"""
    (async () => {{
      try {{
        const token = await __bc_recaptcha('VIDEO_GENERATION');
        const projectId = location.pathname.match(/\\/project\\/([^\\/?#]+)/)?.[1];
        if (!projectId) return {{ error: true, errorDetails: 'Không tìm thấy ID dự án Flow' }};

        const prompt = {json.dumps(prompt)};
        const modelCode = {json.dumps(model_code)};
        const ti_le_code = {ti_le_code};
        const co_code = {co_code};
        const so_count = {so};

        const videoItems = [];
        for (let i = 0; i < so_count; i++) {{
          const u1 = crypto.randomUUID();
          const u2 = crypto.randomUUID();
          videoItems.push([
            [null, null, [[[prompt]]]],
            modelCode,
            ti_le_code,
            null,
            [null, null, null, null, u1, u2],
            null,
            null,
            [co_code]
          ]);
        }}

        const u3 = crypto.randomUUID();
        const inner = [
          videoItems,
          [null, 22, null, null, null, projectId, null, null, null, null, [token, 1]],
          [u3, 2]
        ];

        const res = await __bc_batchexecute('YhhmEf', inner);
        return Object.assign({{}}, res, {{
          model: modelCode,
          ti_le: ti_le_code,
          diem: {json.dumps(m_info["diem"])}
        }});
      }} catch(e) {{
        return {{ error: true, errorDetails: e.toString() }};
      }}
    }})()
    """
    ret = _chay_js(ph, js)
    if not ret:
        raise RuntimeError("Không nhận được phản hồi từ YhhmEf")
    return ret


def hoi_tien_do_video(ph, op_ids):
    """Hỏi tiến độ tạo video qua RPC jwpduf (BatchCheckAsyncVideoGenerationStatus).
    op_ids: list [id thao tác]
    """
    if not op_ids:
        return {"error": True, "errorDetails": "Danh sách op_ids rỗng"}

    js = _JS_BATCHEXECUTE + f"""
    (async () => {{
      try {{
        const opIds = {json.dumps(op_ids)};
        const inner = [null, null, opIds.map(id => [id])];
        return await __bc_batchexecute('jwpduf', inner);
      }} catch(e) {{
        return {{ error: true, errorDetails: e.toString() }};
      }}
    }})()
    """
    return _chay_js(ph, js)


def lay_link_media(ph, media_id):
    """Lấy link media có chữ ký (video hoặc ảnh) qua RPC as29s (GetMedia).
    Trả về dict {error, url, payload}.
    """
    js = _JS_BATCHEXECUTE + f"""
    (async () => {{
      try {{
        const mediaId = {json.dumps(media_id)};
        const res = await __bc_batchexecute('as29s', [mediaId]);
        if (res.error) return res;
        const text = res.rawText || '';
        const m = text.match(/https:\\/\\/flow-content\\.google\\/(?:video|image)\\/[^\\s"'\\\\]+/);
        let url = m ? m[0] : null;
        if (url) {{
          url = url.replace(/\\\\u003d/g, '=').replace(/\\\\u0026/g, '&');
        }}
        return {{ error: false, url: url, payload: res.payload }};
      }} catch(e) {{
        return {{ error: true, errorDetails: e.toString() }};
      }}
    }})()
    """
    return _chay_js(ph, js)


def lay_noi_dung_du_an(ph, project_id=None):
    """Lấy toàn bộ nội dung của dự án qua RPC Zzl0ze (GetProjectContents).
    Trả về dict {error, project_id, items, rawText}.
    """
    js = _JS_BATCHEXECUTE + f"""
    (async () => {{
      try {{
        const pid = {json.dumps(project_id or "")} || location.pathname.match(/\\/project\\/([^\\/?#]+)/)?.[1];
        if (!pid) return {{ error: true, errorDetails: 'Không có project ID' }};
        const res = await __bc_batchexecute('Zzl0ze', ["projects/" + pid]);
        if (res.error) return res;
        const items = (res.payload && res.payload[1]) || [];
        return {{ error: false, project_id: pid, items: items, rawText: res.rawText }};
      }} catch(e) {{
        return {{ error: true, errorDetails: e.toString() }};
      }}
    }})()
    """
    return _chay_js(ph, js)


def tao_anh_batchexecute(ph, prompt, ti_le="16:9", so=2):
    """Gửi trực tiếp lệnh tạo ảnh ogiZ0b (BatchGenerateImages) qua batchexecute.
    Trả về dict {error, payload, rawText}.
    """
    ti_le_code = 1 if "9:16" in str(ti_le) else 3
    so = max(1, min(4, int(so or 2)))

    js = _JS_BATCHEXECUTE + f"""
    (async () => {{
      try {{
        const token = await __bc_recaptcha('IMAGE_GENERATION');
        const projectId = location.pathname.match(/\\/project\\/([^\\/?#]+)/)?.[1];
        if (!projectId) return {{ error: true, errorDetails: 'Không tìm thấy ID dự án Flow' }};

        const prompt = {json.dumps(prompt)};
        const ti_le_code = {ti_le_code};
        const so_count = {so};

        const recSec = [null, 22, null, null, null, projectId, null, null, null, null, [token, 1]];
        const items = [];
        for (let i = 0; i < so_count; i++) {{
          const seed = Math.floor(Math.random() * 2147483647);
          items.push([
            null, null, null, seed, ti_le_code, "BELUGA", null,
            recSec,
            [[[prompt]]],
            null, null, null,
            crypto.randomUUID(), crypto.randomUUID()
          ]);
        }}

        const inner = [null, items];
        return await __bc_batchexecute('ogiZ0b', inner);
      }} catch(e) {{
        return {{ error: true, errorDetails: e.toString() }};
      }}
    }})()
    """
    ret = _chay_js(ph, js)
    if not ret:
        raise RuntimeError("Không nhận được phản hồi từ ogiZ0b")
    return ret


def tach_link_media(van_ban):
    """Trích xuất tất cả các link media flow-content.google/(video|image)/... từ văn bản phản hồi."""
    ra, thay = [], set()
    for m in _URL_MEDIA.finditer(van_ban or ""):
        mid = m.group(1)
        if mid not in thay:
            thay.add(mid)
            ra.append((mid, thoat_url(m.group(0))))
    return ra
