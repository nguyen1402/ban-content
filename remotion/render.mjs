// node render.mjs jobs.json — mỗi job: {comp, props, giay, out}. Đóng gói một lần, render lần lượt.
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const browserExecutable = process.env.BROWSER_EXE || undefined;

const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'index.jsx')});
let ok = 0;
for (const j of jobs) {
  try {
    const props = {...j.props, giay: j.giay};
    const comp = await selectComposition({serveUrl, id: j.comp, inputProps: props, browserExecutable});
    await renderMedia({
      composition: comp, serveUrl, codec: 'h264', outputLocation: j.out,
      inputProps: props, browserExecutable, crf: 20, logLevel: 'error',
    });
    ok++;
    console.log(`OK ${j.out}`);
  } catch (e) {
    console.log(`LOI ${j.out}: ${String(e).slice(0, 300)}`);
  }
}
console.log(`XONG ${ok}/${jobs.length}`);
