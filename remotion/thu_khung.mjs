// node thu_khung.mjs <entry.jsx> <thư mục public nhỏ> <thư mục ra> <tiền tố tên> <khung1,khung2,…>
// 04/11 user ("tối ưu làm sao mà nó nhanh nhất có thể"): dựng thử NHIỀU khung của một cảnh trong MỘT lần đóng gói + MỘT
// trình duyệt (trước: mỗi khung một lần `npx remotion still`, mỗi lần chép cả public 4,1 GB vào bản đóng gói ~20 s).
// public nhỏ = chỉ các ảnh cảnh dùng (liên kết cứng, không chép). In "OK <png>" từng khung hoặc "LOI <lỗi>".
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const [entry, pub, ra, ten, khung] = process.argv.slice(2);
const browserExecutable = process.env.BROWSER_EXE || undefined;
const GL = process.env.RENDER_GL === 'cpu' ? undefined : (process.env.RENDER_GL || 'angle');
let serveUrl = null;
let browser = null;
try {
  serveUrl = await bundle({entryPoint: path.resolve(entry), publicDir: path.resolve(pub)});
  browser = await openBrowser('chrome', {browserExecutable, chromiumOptions: GL ? {gl: GL} : {}});
  const comp = await selectComposition({serveUrl, id: 'thu', browserExecutable, puppeteerInstance: browser});
  for (const k of khung.split(',').map(Number)) {
    const out = path.join(ra, `${ten}_${k}.png`);
    await renderStill({composition: comp, serveUrl, output: out, frame: Math.min(k, comp.durationInFrames - 1),
      browserExecutable, puppeteerInstance: browser, chromiumOptions: GL ? {gl: GL} : {}, logLevel: 'error'});
    console.log(`OK ${out}`);
  }
} catch (e) {
  console.log(`LOI ${String(e && e.stack || e).slice(0, 2500)}`);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close({silent: true}).catch(() => {});
  try { if (serveUrl && fs.existsSync(serveUrl)) fs.rmSync(serveUrl, {recursive: true, force: true}); } catch {}
}
