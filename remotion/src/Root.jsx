import React from 'react';
import {Composition} from 'remotion';
import {BanDo} from './BanDo.jsx';
import {BanDoNen} from './BanDoNen.jsx';
import {BieuDo} from './BieuDo.jsx';
import {BangGiay} from './BangGiay.jsx';
import {NhanVat} from './NhanVat.jsx';
import {MinhHoa} from './MinhHoa.jsx';
import {CanhMoTa} from './CanhMoTa.jsx';

const FPS = 30;
// Thời lượng lấy từ props.giay (Python truyền theo độ dài giọng đọc của cảnh).
const meta = async ({props}) => ({
  durationInFrames: Math.max(30, Math.round((props.giay || 5) * FPS)),
});

export const Root = () => (
  <>
    <Composition id="BanDo" component={BanDo} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5}} calculateMetadata={meta} />
    <Composition id="BanDoNen" component={BanDoNen} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, lop: [{z: 10, ox: 0, oy: 0, w: 256, h: 256, src: ''}]}} calculateMetadata={meta} />
    <Composition id="BangGiay" component={BangGiay} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, nhip: []}} calculateMetadata={meta} />
    <Composition id="BieuDo" component={BieuDo} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5}} calculateMetadata={meta} />
    <Composition id="MinhHoa" component={MinhHoa} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, kieu: 'quy_trinh', muc: []}} calculateMetadata={meta} />
    <Composition id="CanhMoTa" component={CanhMoTa} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, nen: '#0b0d12', lop: []}} calculateMetadata={meta} />
    <Composition id="NhanVat" component={NhanVat} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, anh: '', nen: '', kieu: 'giua'}} calculateMetadata={meta} />
  </>
);
