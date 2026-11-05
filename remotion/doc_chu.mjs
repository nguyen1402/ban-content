// node doc_chu.mjs <entry.jsx> <thư mục public nhỏ> <thư mục tạm> <khung1,khung2,…>
// 05/11 user ("số liệu bị sai khi dựng remotion"): dựng thử nhiều khung ở cỡ rất nhỏ, entry bọc cảnh in ra (console) mọi
// chữ CÓ SỐ đang nhìn thấy trên khung — dòng "CHU {f, ds:[[đường, chữ]]}". Bên Python so với số trong lời kể.
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const [entry, pub, ra, khung] = process.argv.slice(2);
const browserExecutable = process.env.BROWSER_EXE || undefined;
let serveUrl = null;
let browser = null;
const onBrowserLog = (l) => { if (process.env.DOC_GO) console.log('LOG', l.type, String(l.text).slice(0, 200)); if (String(l.text).startsWith('CHU ')) console.log(l.text); };
try {
  serveUrl = await bundle({entryPoint: path.resolve(entry), publicDir: path.resolve(pub)});
  browser = await openBrowser('chrome', {browserExecutable});
  const comp = await selectComposition({serveUrl, id: 'thu', browserExecutable, puppeteerInstance: browser});
  for (const k of khung.split(',').map(Number)) {
    await renderStill({composition: comp, serveUrl, output: path.join(ra, `_doc_${k}.jpeg`), imageFormat: 'jpeg', scale: 0.1,
      frame: Math.min(k, comp.durationInFrames - 1), browserExecutable, puppeteerInstance: browser, logLevel: 'error', onBrowserLog});
  }
  console.log('XONG');
} catch (e) {
  console.log(`LOI ${String(e && e.stack || e).slice(0, 1500)}`);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close({silent: true}).catch(() => {});
  try { if (serveUrl && fs.existsSync(serveUrl)) fs.rmSync(serveUrl, {recursive: true, force: true}); } catch {}
}
