// node sua_lop_dong_goi.mjs <cảnh.jsx> <tệp ra.js> [giọng đọc (đường trong public)]
// 05/11: đóng gói MỘT cảnh AI + Remotion Player thành một tệp JS cho trang 🎚 sửa lớp (window.SuaLop). 'remotion' trỏ vào
// sua_lop_shim.jsx (bọc Interactive / Img để đè thông số lớp lúc phát), shim trỏ tiếp vào Remotion thật.
import {build} from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const [canh, ra, giong = ''] = process.argv.slice(2);
const SHIM = path.join(here, 'sua_lop_shim.jsx');
const that = require.resolve('remotion');
const entry = path.join(path.dirname(ra), `_vao_${path.basename(ra, '.js')}.jsx`);
fs.writeFileSync(entry, `
import React from 'react';
import {createRoot} from 'react-dom/client';
import {Player} from '@remotion/player';
import {Audio, staticFile} from 'remotion';
import {Canh} from ${JSON.stringify(path.resolve(canh).replace(/\\/g, '/'))};
import {kho} from ${JSON.stringify(SHIM.replace(/\\/g, '/'))};
const GIONG = ${JSON.stringify(giong)};
const Boc = (p) => { React.useSyncExternalStore(kho.nghe, kho.ban); return <>{React.createElement(Canh, p)}{GIONG ? <Audio src={staticFile(GIONG)} /> : null}</>; };
window.SuaLop = {
  kho,
  mount(el, {props, khung}) {
    const ref = React.createRef();
    createRoot(el).render(<Player ref={ref} component={Boc} inputProps={props} durationInFrames={khung} fps={30}
      compositionWidth={1920} compositionHeight={1080} style={{width: '100%', height: '100%'}} clickToPlay={false}
      acknowledgeRemotionLicense numberOfSharedAudioTags={2} />);
    return ref;
  },
};
`);
try {
  await build({
    entryPoints: [entry], outfile: ra, bundle: true, format: 'iife', jsx: 'automatic', minify: true,
    loader: {'.jsx': 'jsx', '.js': 'jsx'}, define: {'process.env.NODE_ENV': '"production"'}, logLevel: 'error',
    absWorkingDir: here, nodePaths: [path.join(here, 'node_modules')],
    plugins: [{
      name: 'remotion-shim',
      setup(b) {
        b.onResolve({filter: /^remotion$/}, (a) => ({path: a.importer === SHIM ? that : SHIM}));
        b.onResolve({filter: /^remotion-goc$/}, () => ({path: that}));
      },
    }],
  });
  console.log('OK');
} catch (e) {
  console.log('LOI ' + String(e && e.message || e).slice(0, 3000));
  process.exitCode = 1;
} finally {
  try { fs.unlinkSync(entry); } catch {}
}
