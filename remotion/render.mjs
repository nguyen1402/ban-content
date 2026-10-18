// node render.mjs jobs.json — mỗi job: {comp, props, giay, out}. Đóng gói một lần, mở trình duyệt MỘT lần dùng chung,
// render SONG SONG nhiều clip (13/10 user: "cho luôn phần render song song cho nhanh"). Số clip cùng lúc: RENDER_SONG_SONG
// (mặc định 3); mỗi clip được chia đều số luồng CPU; vẽ bằng GPU (gl=angle, RENDER_GL=cpu để tắt).
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const browserExecutable = process.env.BROWSER_EXE || undefined;
const SONG_SONG = Math.max(1, Math.min(jobs.length || 1, parseInt(process.env.RENDER_SONG_SONG || '3', 10)));
const LUONG = parseInt(process.env.RENDER_LUONG || '0', 10) || Math.max(2, Math.floor(os.cpus().length / SONG_SONG));

// Dọn dẹp bundle Webpack tạm của Remotion để không phình ổ C (mỗi bundle ~2.4GB)
function donDepBundle(targetPath) {
  try {
    if (targetPath && fs.existsSync(targetPath)) {
      fs.rmSync(targetPath, {recursive: true, force: true, maxRetries: 3, retryDelay: 500});
    }
  } catch {}
}

// Tự động quét và dọn các bundle rác cũ còn sót lại từ các lần trước trong thư mục Temp
function donDepBundleCu() {
  try {
    const tmpDir = os.tmpdir();
    const files = fs.readdirSync(tmpDir);
    for (const f of files) {
      if (f.startsWith('remotion-webpack-bundle-')) {
        const full = path.join(tmpDir, f);
        try {
          fs.rmSync(full, {recursive: true, force: true});
        } catch {}
      }
    }
  } catch {}
}

// Dọn dẹp bundle cũ còn sót lại trước khi bắt đầu
donDepBundleCu();

const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'index.jsx')});

// Đăng ký bắt sự kiện ngắt tiến trình để luôn dọn bundle nếu bị dừng đột ngột
const cleanupOnExit = () => donDepBundle(serveUrl);
process.on('SIGINT', () => { cleanupOnExit(); process.exit(130); });
process.on('SIGTERM', () => { cleanupOnExit(); process.exit(143); });

// 13/10 đo 6 clip: CPU 1 luồng 68 s; GPU (angle) 47 s; GPU + 3 clip song song 38 s -> mặc định GPU + 3
const GL = process.env.RENDER_GL === 'cpu' ? undefined : (process.env.RENDER_GL || 'angle');
let browser = null;
let ok = 0;
let ke = 0;

try {
  browser = await openBrowser('chrome', {browserExecutable, chromiumOptions: GL ? {gl: GL} : {}});

  async function tho() {
    while (ke < jobs.length) {
      const j = jobs[ke++];
      try {
        const props = {...j.props, giay: j.giay};
        const comp = await selectComposition({serveUrl, id: j.comp, inputProps: props, browserExecutable, puppeteerInstance: browser});
        await renderMedia({
          composition: comp, serveUrl, codec: 'h264', outputLocation: j.out, inputProps: props, browserExecutable,
          puppeteerInstance: browser, concurrency: LUONG, crf: 20, logLevel: 'error', chromiumOptions: GL ? {gl: GL} : {},
        });
        ok++;
        console.log(`OK ${j.out}`);
      } catch (e) {
        console.log(`LOI ${j.out}: ${String(e).slice(0, 300)}`);
      }
    }
  }

  await Promise.all(Array.from({length: SONG_SONG}, tho));
} finally {
  if (browser) {
    await browser.close({silent: true}).catch(() => {});
  }
  donDepBundle(serveUrl);
}

console.log(`XONG ${ok}/${jobs.length}`);
