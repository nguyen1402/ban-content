import React from 'react';
import {Composition} from 'remotion';
import {BanDo} from './BanDo.jsx';
import {BanDoNen} from './BanDoNen.jsx';
import {BieuDo} from './BieuDo.jsx';
import {BangGiay} from './BangGiay.jsx';
import {NhanVat} from './NhanVat.jsx';
import {MinhHoa} from './MinhHoa.jsx';
import {CanhMoTa} from './CanhMoTa.jsx';
import {NhanY} from './NhanY.jsx';
import {NuocDang, nuocDangSchema, NUOC_DANG_MAC_DINH} from './Canh3D.jsx';
import {Folder} from 'remotion';
import {GiaiPhau, giaiPhauSchema, GIAI_PHAU_MAC_DINH} from './GiaiPhau.jsx';
// NHAN_Y_AI_IMPORT_BAT_DAU
import {coGiong} from './ai/thu_vien.jsx';
import {Canh as AiCalocCau106, schema as AiCalocCau106Schema} from './ai/caloc_cau106.jsx';
const AiCalocCau106G = coGiong(AiCalocCau106, "nhan_y/giong_caloc_cau106.wav");
import {Canh as AiCalocCau20, schema as AiCalocCau20Schema} from './ai/caloc_cau20.jsx';
const AiCalocCau20G = coGiong(AiCalocCau20, "nhan_y/giong_caloc_cau20.wav");
import {Canh as AiCalocCau33, schema as AiCalocCau33Schema} from './ai/caloc_cau33.jsx';
const AiCalocCau33G = coGiong(AiCalocCau33, "nhan_y/giong_caloc_cau33.wav");
import {Canh as AiCalocCau53, schema as AiCalocCau53Schema} from './ai/caloc_cau53.jsx';
const AiCalocCau53G = coGiong(AiCalocCau53, "nhan_y/giong_caloc_cau53.wav");
import {Canh as AiCalocCau57, schema as AiCalocCau57Schema} from './ai/caloc_cau57.jsx';
const AiCalocCau57G = coGiong(AiCalocCau57, "nhan_y/giong_caloc_cau57.wav");
import {Canh as AiCalocCau64, schema as AiCalocCau64Schema} from './ai/caloc_cau64.jsx';
const AiCalocCau64G = coGiong(AiCalocCau64, "nhan_y/giong_caloc_cau64.wav");
import {Canh as AiCalocCau73, schema as AiCalocCau73Schema} from './ai/caloc_cau73.jsx';
const AiCalocCau73G = coGiong(AiCalocCau73, "nhan_y/giong_caloc_cau73.wav");
import {Canh as AiCalocCau87, schema as AiCalocCau87Schema} from './ai/caloc_cau87.jsx';
const AiCalocCau87G = coGiong(AiCalocCau87, "nhan_y/giong_caloc_cau87.wav");
import {Canh as AiCalocCau99, schema as AiCalocCau99Schema} from './ai/caloc_cau99.jsx';
const AiCalocCau99G = coGiong(AiCalocCau99, "nhan_y/giong_caloc_cau99.wav");
import {Canh as AiLopxeCau1, schema as AiLopxeCau1Schema} from './ai/lopxe_cau1.jsx';
const AiLopxeCau1G = coGiong(AiLopxeCau1, "nhan_y/giong_lopxe_cau1.wav");
import {Canh as AiLopxeCau10, schema as AiLopxeCau10Schema} from './ai/lopxe_cau10.jsx';
const AiLopxeCau10G = coGiong(AiLopxeCau10, "nhan_y/giong_lopxe_cau10.wav");
import {Canh as AiLopxeCau100, schema as AiLopxeCau100Schema} from './ai/lopxe_cau100.jsx';
const AiLopxeCau100G = coGiong(AiLopxeCau100, "nhan_y/giong_lopxe_cau100.wav");
import {Canh as AiLopxeCau101, schema as AiLopxeCau101Schema} from './ai/lopxe_cau101.jsx';
const AiLopxeCau101G = coGiong(AiLopxeCau101, "nhan_y/giong_lopxe_cau101.wav");
import {Canh as AiLopxeCau102, schema as AiLopxeCau102Schema} from './ai/lopxe_cau102.jsx';
const AiLopxeCau102G = coGiong(AiLopxeCau102, "nhan_y/giong_lopxe_cau102.wav");
import {Canh as AiLopxeCau103, schema as AiLopxeCau103Schema} from './ai/lopxe_cau103.jsx';
const AiLopxeCau103G = coGiong(AiLopxeCau103, "nhan_y/giong_lopxe_cau103.wav");
import {Canh as AiLopxeCau104, schema as AiLopxeCau104Schema} from './ai/lopxe_cau104.jsx';
const AiLopxeCau104G = coGiong(AiLopxeCau104, "nhan_y/giong_lopxe_cau104.wav");
import {Canh as AiLopxeCau105, schema as AiLopxeCau105Schema} from './ai/lopxe_cau105.jsx';
const AiLopxeCau105G = coGiong(AiLopxeCau105, "nhan_y/giong_lopxe_cau105.wav");
import {Canh as AiLopxeCau106, schema as AiLopxeCau106Schema} from './ai/lopxe_cau106.jsx';
const AiLopxeCau106G = coGiong(AiLopxeCau106, "nhan_y/giong_lopxe_cau106.wav");
import {Canh as AiLopxeCau107, schema as AiLopxeCau107Schema} from './ai/lopxe_cau107.jsx';
const AiLopxeCau107G = coGiong(AiLopxeCau107, "nhan_y/giong_lopxe_cau107.wav");
import {Canh as AiLopxeCau108, schema as AiLopxeCau108Schema} from './ai/lopxe_cau108.jsx';
const AiLopxeCau108G = coGiong(AiLopxeCau108, "nhan_y/giong_lopxe_cau108.wav");
import {Canh as AiLopxeCau109, schema as AiLopxeCau109Schema} from './ai/lopxe_cau109.jsx';
const AiLopxeCau109G = coGiong(AiLopxeCau109, "nhan_y/giong_lopxe_cau109.wav");
import {Canh as AiLopxeCau11, schema as AiLopxeCau11Schema} from './ai/lopxe_cau11.jsx';
const AiLopxeCau11G = coGiong(AiLopxeCau11, "nhan_y/giong_lopxe_cau11.wav");
import {Canh as AiLopxeCau110, schema as AiLopxeCau110Schema} from './ai/lopxe_cau110.jsx';
const AiLopxeCau110G = coGiong(AiLopxeCau110, "nhan_y/giong_lopxe_cau110.wav");
import {Canh as AiLopxeCau111, schema as AiLopxeCau111Schema} from './ai/lopxe_cau111.jsx';
const AiLopxeCau111G = coGiong(AiLopxeCau111, "nhan_y/giong_lopxe_cau111.wav");
import {Canh as AiLopxeCau112, schema as AiLopxeCau112Schema} from './ai/lopxe_cau112.jsx';
const AiLopxeCau112G = coGiong(AiLopxeCau112, "nhan_y/giong_lopxe_cau112.wav");
import {Canh as AiLopxeCau113, schema as AiLopxeCau113Schema} from './ai/lopxe_cau113.jsx';
const AiLopxeCau113G = coGiong(AiLopxeCau113, "nhan_y/giong_lopxe_cau113.wav");
import {Canh as AiLopxeCau114, schema as AiLopxeCau114Schema} from './ai/lopxe_cau114.jsx';
const AiLopxeCau114G = coGiong(AiLopxeCau114, "nhan_y/giong_lopxe_cau114.wav");
import {Canh as AiLopxeCau115, schema as AiLopxeCau115Schema} from './ai/lopxe_cau115.jsx';
const AiLopxeCau115G = coGiong(AiLopxeCau115, "nhan_y/giong_lopxe_cau115.wav");
import {Canh as AiLopxeCau116, schema as AiLopxeCau116Schema} from './ai/lopxe_cau116.jsx';
const AiLopxeCau116G = coGiong(AiLopxeCau116, "nhan_y/giong_lopxe_cau116.wav");
import {Canh as AiLopxeCau117, schema as AiLopxeCau117Schema} from './ai/lopxe_cau117.jsx';
const AiLopxeCau117G = coGiong(AiLopxeCau117, "nhan_y/giong_lopxe_cau117.wav");
import {Canh as AiLopxeCau118, schema as AiLopxeCau118Schema} from './ai/lopxe_cau118.jsx';
const AiLopxeCau118G = coGiong(AiLopxeCau118, "nhan_y/giong_lopxe_cau118.wav");
import {Canh as AiLopxeCau119, schema as AiLopxeCau119Schema} from './ai/lopxe_cau119.jsx';
const AiLopxeCau119G = coGiong(AiLopxeCau119, "nhan_y/giong_lopxe_cau119.wav");
import {Canh as AiLopxeCau12, schema as AiLopxeCau12Schema} from './ai/lopxe_cau12.jsx';
const AiLopxeCau12G = coGiong(AiLopxeCau12, "nhan_y/giong_lopxe_cau12.wav");
import {Canh as AiLopxeCau120, schema as AiLopxeCau120Schema} from './ai/lopxe_cau120.jsx';
const AiLopxeCau120G = coGiong(AiLopxeCau120, "nhan_y/giong_lopxe_cau120.wav");
import {Canh as AiLopxeCau121, schema as AiLopxeCau121Schema} from './ai/lopxe_cau121.jsx';
const AiLopxeCau121G = coGiong(AiLopxeCau121, "nhan_y/giong_lopxe_cau121.wav");
import {Canh as AiLopxeCau13, schema as AiLopxeCau13Schema} from './ai/lopxe_cau13.jsx';
const AiLopxeCau13G = coGiong(AiLopxeCau13, "nhan_y/giong_lopxe_cau13.wav");
import {Canh as AiLopxeCau14, schema as AiLopxeCau14Schema} from './ai/lopxe_cau14.jsx';
const AiLopxeCau14G = coGiong(AiLopxeCau14, "nhan_y/giong_lopxe_cau14.wav");
import {Canh as AiLopxeCau15, schema as AiLopxeCau15Schema} from './ai/lopxe_cau15.jsx';
const AiLopxeCau15G = coGiong(AiLopxeCau15, "nhan_y/giong_lopxe_cau15.wav");
import {Canh as AiLopxeCau16, schema as AiLopxeCau16Schema} from './ai/lopxe_cau16.jsx';
const AiLopxeCau16G = coGiong(AiLopxeCau16, "nhan_y/giong_lopxe_cau16.wav");
import {Canh as AiLopxeCau17, schema as AiLopxeCau17Schema} from './ai/lopxe_cau17.jsx';
const AiLopxeCau17G = coGiong(AiLopxeCau17, "nhan_y/giong_lopxe_cau17.wav");
import {Canh as AiLopxeCau18, schema as AiLopxeCau18Schema} from './ai/lopxe_cau18.jsx';
const AiLopxeCau18G = coGiong(AiLopxeCau18, "nhan_y/giong_lopxe_cau18.wav");
import {Canh as AiLopxeCau19, schema as AiLopxeCau19Schema} from './ai/lopxe_cau19.jsx';
const AiLopxeCau19G = coGiong(AiLopxeCau19, "nhan_y/giong_lopxe_cau19.wav");
import {Canh as AiLopxeCau2, schema as AiLopxeCau2Schema} from './ai/lopxe_cau2.jsx';
const AiLopxeCau2G = coGiong(AiLopxeCau2, "nhan_y/giong_lopxe_cau2.wav");
import {Canh as AiLopxeCau20, schema as AiLopxeCau20Schema} from './ai/lopxe_cau20.jsx';
const AiLopxeCau20G = coGiong(AiLopxeCau20, "nhan_y/giong_lopxe_cau20.wav");
import {Canh as AiLopxeCau21, schema as AiLopxeCau21Schema} from './ai/lopxe_cau21.jsx';
const AiLopxeCau21G = coGiong(AiLopxeCau21, "nhan_y/giong_lopxe_cau21.wav");
import {Canh as AiLopxeCau22, schema as AiLopxeCau22Schema} from './ai/lopxe_cau22.jsx';
const AiLopxeCau22G = coGiong(AiLopxeCau22, "nhan_y/giong_lopxe_cau22.wav");
import {Canh as AiLopxeCau23, schema as AiLopxeCau23Schema} from './ai/lopxe_cau23.jsx';
const AiLopxeCau23G = coGiong(AiLopxeCau23, "nhan_y/giong_lopxe_cau23.wav");
import {Canh as AiLopxeCau24, schema as AiLopxeCau24Schema} from './ai/lopxe_cau24.jsx';
const AiLopxeCau24G = coGiong(AiLopxeCau24, "nhan_y/giong_lopxe_cau24.wav");
import {Canh as AiLopxeCau25, schema as AiLopxeCau25Schema} from './ai/lopxe_cau25.jsx';
const AiLopxeCau25G = coGiong(AiLopxeCau25, "nhan_y/giong_lopxe_cau25.wav");
import {Canh as AiLopxeCau26, schema as AiLopxeCau26Schema} from './ai/lopxe_cau26.jsx';
const AiLopxeCau26G = coGiong(AiLopxeCau26, "nhan_y/giong_lopxe_cau26.wav");
import {Canh as AiLopxeCau27, schema as AiLopxeCau27Schema} from './ai/lopxe_cau27.jsx';
const AiLopxeCau27G = coGiong(AiLopxeCau27, "nhan_y/giong_lopxe_cau27.wav");
import {Canh as AiLopxeCau29, schema as AiLopxeCau29Schema} from './ai/lopxe_cau29.jsx';
const AiLopxeCau29G = coGiong(AiLopxeCau29, "nhan_y/giong_lopxe_cau29.wav");
import {Canh as AiLopxeCau3, schema as AiLopxeCau3Schema} from './ai/lopxe_cau3.jsx';
const AiLopxeCau3G = coGiong(AiLopxeCau3, "nhan_y/giong_lopxe_cau3.wav");
import {Canh as AiLopxeCau30, schema as AiLopxeCau30Schema} from './ai/lopxe_cau30.jsx';
const AiLopxeCau30G = coGiong(AiLopxeCau30, "nhan_y/giong_lopxe_cau30.wav");
import {Canh as AiLopxeCau31, schema as AiLopxeCau31Schema} from './ai/lopxe_cau31.jsx';
const AiLopxeCau31G = coGiong(AiLopxeCau31, "nhan_y/giong_lopxe_cau31.wav");
import {Canh as AiLopxeCau32, schema as AiLopxeCau32Schema} from './ai/lopxe_cau32.jsx';
const AiLopxeCau32G = coGiong(AiLopxeCau32, "nhan_y/giong_lopxe_cau32.wav");
import {Canh as AiLopxeCau33, schema as AiLopxeCau33Schema} from './ai/lopxe_cau33.jsx';
const AiLopxeCau33G = coGiong(AiLopxeCau33, "nhan_y/giong_lopxe_cau33.wav");
import {Canh as AiLopxeCau34, schema as AiLopxeCau34Schema} from './ai/lopxe_cau34.jsx';
const AiLopxeCau34G = coGiong(AiLopxeCau34, "nhan_y/giong_lopxe_cau34.wav");
import {Canh as AiLopxeCau35, schema as AiLopxeCau35Schema} from './ai/lopxe_cau35.jsx';
const AiLopxeCau35G = coGiong(AiLopxeCau35, "nhan_y/giong_lopxe_cau35.wav");
import {Canh as AiLopxeCau36, schema as AiLopxeCau36Schema} from './ai/lopxe_cau36.jsx';
const AiLopxeCau36G = coGiong(AiLopxeCau36, "nhan_y/giong_lopxe_cau36.wav");
import {Canh as AiLopxeCau37, schema as AiLopxeCau37Schema} from './ai/lopxe_cau37.jsx';
const AiLopxeCau37G = coGiong(AiLopxeCau37, "nhan_y/giong_lopxe_cau37.wav");
import {Canh as AiLopxeCau38, schema as AiLopxeCau38Schema} from './ai/lopxe_cau38.jsx';
const AiLopxeCau38G = coGiong(AiLopxeCau38, "nhan_y/giong_lopxe_cau38.wav");
import {Canh as AiLopxeCau39, schema as AiLopxeCau39Schema} from './ai/lopxe_cau39.jsx';
const AiLopxeCau39G = coGiong(AiLopxeCau39, "nhan_y/giong_lopxe_cau39.wav");
import {Canh as AiLopxeCau4, schema as AiLopxeCau4Schema} from './ai/lopxe_cau4.jsx';
const AiLopxeCau4G = coGiong(AiLopxeCau4, "nhan_y/giong_lopxe_cau4.wav");
import {Canh as AiLopxeCau40, schema as AiLopxeCau40Schema} from './ai/lopxe_cau40.jsx';
const AiLopxeCau40G = coGiong(AiLopxeCau40, "nhan_y/giong_lopxe_cau40.wav");
import {Canh as AiLopxeCau41, schema as AiLopxeCau41Schema} from './ai/lopxe_cau41.jsx';
const AiLopxeCau41G = coGiong(AiLopxeCau41, "nhan_y/giong_lopxe_cau41.wav");
import {Canh as AiLopxeCau42, schema as AiLopxeCau42Schema} from './ai/lopxe_cau42.jsx';
const AiLopxeCau42G = coGiong(AiLopxeCau42, "nhan_y/giong_lopxe_cau42.wav");
import {Canh as AiLopxeCau43, schema as AiLopxeCau43Schema} from './ai/lopxe_cau43.jsx';
const AiLopxeCau43G = coGiong(AiLopxeCau43, "nhan_y/giong_lopxe_cau43.wav");
import {Canh as AiLopxeCau44, schema as AiLopxeCau44Schema} from './ai/lopxe_cau44.jsx';
const AiLopxeCau44G = coGiong(AiLopxeCau44, "nhan_y/giong_lopxe_cau44.wav");
import {Canh as AiLopxeCau45, schema as AiLopxeCau45Schema} from './ai/lopxe_cau45.jsx';
const AiLopxeCau45G = coGiong(AiLopxeCau45, "nhan_y/giong_lopxe_cau45.wav");
import {Canh as AiLopxeCau46, schema as AiLopxeCau46Schema} from './ai/lopxe_cau46.jsx';
const AiLopxeCau46G = coGiong(AiLopxeCau46, "nhan_y/giong_lopxe_cau46.wav");
import {Canh as AiLopxeCau48, schema as AiLopxeCau48Schema} from './ai/lopxe_cau48.jsx';
const AiLopxeCau48G = coGiong(AiLopxeCau48, "nhan_y/giong_lopxe_cau48.wav");
import {Canh as AiLopxeCau49, schema as AiLopxeCau49Schema} from './ai/lopxe_cau49.jsx';
const AiLopxeCau49G = coGiong(AiLopxeCau49, "nhan_y/giong_lopxe_cau49.wav");
import {Canh as AiLopxeCau5, schema as AiLopxeCau5Schema} from './ai/lopxe_cau5.jsx';
const AiLopxeCau5G = coGiong(AiLopxeCau5, "nhan_y/giong_lopxe_cau5.wav");
import {Canh as AiLopxeCau50, schema as AiLopxeCau50Schema} from './ai/lopxe_cau50.jsx';
const AiLopxeCau50G = coGiong(AiLopxeCau50, "nhan_y/giong_lopxe_cau50.wav");
import {Canh as AiLopxeCau51, schema as AiLopxeCau51Schema} from './ai/lopxe_cau51.jsx';
const AiLopxeCau51G = coGiong(AiLopxeCau51, "nhan_y/giong_lopxe_cau51.wav");
import {Canh as AiLopxeCau52, schema as AiLopxeCau52Schema} from './ai/lopxe_cau52.jsx';
const AiLopxeCau52G = coGiong(AiLopxeCau52, "nhan_y/giong_lopxe_cau52.wav");
import {Canh as AiLopxeCau53, schema as AiLopxeCau53Schema} from './ai/lopxe_cau53.jsx';
const AiLopxeCau53G = coGiong(AiLopxeCau53, "nhan_y/giong_lopxe_cau53.wav");
import {Canh as AiLopxeCau54, schema as AiLopxeCau54Schema} from './ai/lopxe_cau54.jsx';
const AiLopxeCau54G = coGiong(AiLopxeCau54, "nhan_y/giong_lopxe_cau54.wav");
import {Canh as AiLopxeCau55, schema as AiLopxeCau55Schema} from './ai/lopxe_cau55.jsx';
const AiLopxeCau55G = coGiong(AiLopxeCau55, "nhan_y/giong_lopxe_cau55.wav");
import {Canh as AiLopxeCau56, schema as AiLopxeCau56Schema} from './ai/lopxe_cau56.jsx';
const AiLopxeCau56G = coGiong(AiLopxeCau56, "nhan_y/giong_lopxe_cau56.wav");
import {Canh as AiLopxeCau57, schema as AiLopxeCau57Schema} from './ai/lopxe_cau57.jsx';
const AiLopxeCau57G = coGiong(AiLopxeCau57, "nhan_y/giong_lopxe_cau57.wav");
import {Canh as AiLopxeCau59, schema as AiLopxeCau59Schema} from './ai/lopxe_cau59.jsx';
const AiLopxeCau59G = coGiong(AiLopxeCau59, "nhan_y/giong_lopxe_cau59.wav");
import {Canh as AiLopxeCau6, schema as AiLopxeCau6Schema} from './ai/lopxe_cau6.jsx';
const AiLopxeCau6G = coGiong(AiLopxeCau6, "nhan_y/giong_lopxe_cau6.wav");
import {Canh as AiLopxeCau61, schema as AiLopxeCau61Schema} from './ai/lopxe_cau61.jsx';
const AiLopxeCau61G = coGiong(AiLopxeCau61, "nhan_y/giong_lopxe_cau61.wav");
import {Canh as AiLopxeCau62, schema as AiLopxeCau62Schema} from './ai/lopxe_cau62.jsx';
const AiLopxeCau62G = coGiong(AiLopxeCau62, "nhan_y/giong_lopxe_cau62.wav");
import {Canh as AiLopxeCau63, schema as AiLopxeCau63Schema} from './ai/lopxe_cau63.jsx';
const AiLopxeCau63G = coGiong(AiLopxeCau63, "nhan_y/giong_lopxe_cau63.wav");
import {Canh as AiLopxeCau64, schema as AiLopxeCau64Schema} from './ai/lopxe_cau64.jsx';
const AiLopxeCau64G = coGiong(AiLopxeCau64, "nhan_y/giong_lopxe_cau64.wav");
import {Canh as AiLopxeCau65, schema as AiLopxeCau65Schema} from './ai/lopxe_cau65.jsx';
const AiLopxeCau65G = coGiong(AiLopxeCau65, "nhan_y/giong_lopxe_cau65.wav");
import {Canh as AiLopxeCau67, schema as AiLopxeCau67Schema} from './ai/lopxe_cau67.jsx';
const AiLopxeCau67G = coGiong(AiLopxeCau67, "nhan_y/giong_lopxe_cau67.wav");
import {Canh as AiLopxeCau68, schema as AiLopxeCau68Schema} from './ai/lopxe_cau68.jsx';
const AiLopxeCau68G = coGiong(AiLopxeCau68, "nhan_y/giong_lopxe_cau68.wav");
import {Canh as AiLopxeCau69, schema as AiLopxeCau69Schema} from './ai/lopxe_cau69.jsx';
const AiLopxeCau69G = coGiong(AiLopxeCau69, "nhan_y/giong_lopxe_cau69.wav");
import {Canh as AiLopxeCau7, schema as AiLopxeCau7Schema} from './ai/lopxe_cau7.jsx';
const AiLopxeCau7G = coGiong(AiLopxeCau7, "nhan_y/giong_lopxe_cau7.wav");
import {Canh as AiLopxeCau70, schema as AiLopxeCau70Schema} from './ai/lopxe_cau70.jsx';
const AiLopxeCau70G = coGiong(AiLopxeCau70, "nhan_y/giong_lopxe_cau70.wav");
import {Canh as AiLopxeCau71, schema as AiLopxeCau71Schema} from './ai/lopxe_cau71.jsx';
const AiLopxeCau71G = coGiong(AiLopxeCau71, "nhan_y/giong_lopxe_cau71.wav");
import {Canh as AiLopxeCau72, schema as AiLopxeCau72Schema} from './ai/lopxe_cau72.jsx';
const AiLopxeCau72G = coGiong(AiLopxeCau72, "nhan_y/giong_lopxe_cau72.wav");
import {Canh as AiLopxeCau73, schema as AiLopxeCau73Schema} from './ai/lopxe_cau73.jsx';
const AiLopxeCau73G = coGiong(AiLopxeCau73, "nhan_y/giong_lopxe_cau73.wav");
import {Canh as AiLopxeCau74, schema as AiLopxeCau74Schema} from './ai/lopxe_cau74.jsx';
const AiLopxeCau74G = coGiong(AiLopxeCau74, "nhan_y/giong_lopxe_cau74.wav");
import {Canh as AiLopxeCau75, schema as AiLopxeCau75Schema} from './ai/lopxe_cau75.jsx';
const AiLopxeCau75G = coGiong(AiLopxeCau75, "nhan_y/giong_lopxe_cau75.wav");
import {Canh as AiLopxeCau76, schema as AiLopxeCau76Schema} from './ai/lopxe_cau76.jsx';
const AiLopxeCau76G = coGiong(AiLopxeCau76, "nhan_y/giong_lopxe_cau76.wav");
import {Canh as AiLopxeCau77, schema as AiLopxeCau77Schema} from './ai/lopxe_cau77.jsx';
const AiLopxeCau77G = coGiong(AiLopxeCau77, "nhan_y/giong_lopxe_cau77.wav");
import {Canh as AiLopxeCau78, schema as AiLopxeCau78Schema} from './ai/lopxe_cau78.jsx';
const AiLopxeCau78G = coGiong(AiLopxeCau78, "nhan_y/giong_lopxe_cau78.wav");
import {Canh as AiLopxeCau79, schema as AiLopxeCau79Schema} from './ai/lopxe_cau79.jsx';
const AiLopxeCau79G = coGiong(AiLopxeCau79, "nhan_y/giong_lopxe_cau79.wav");
import {Canh as AiLopxeCau8, schema as AiLopxeCau8Schema} from './ai/lopxe_cau8.jsx';
const AiLopxeCau8G = coGiong(AiLopxeCau8, "nhan_y/giong_lopxe_cau8.wav");
import {Canh as AiLopxeCau80, schema as AiLopxeCau80Schema} from './ai/lopxe_cau80.jsx';
const AiLopxeCau80G = coGiong(AiLopxeCau80, "nhan_y/giong_lopxe_cau80.wav");
import {Canh as AiLopxeCau81, schema as AiLopxeCau81Schema} from './ai/lopxe_cau81.jsx';
const AiLopxeCau81G = coGiong(AiLopxeCau81, "nhan_y/giong_lopxe_cau81.wav");
import {Canh as AiLopxeCau82, schema as AiLopxeCau82Schema} from './ai/lopxe_cau82.jsx';
const AiLopxeCau82G = coGiong(AiLopxeCau82, "nhan_y/giong_lopxe_cau82.wav");
import {Canh as AiLopxeCau83, schema as AiLopxeCau83Schema} from './ai/lopxe_cau83.jsx';
const AiLopxeCau83G = coGiong(AiLopxeCau83, "nhan_y/giong_lopxe_cau83.wav");
import {Canh as AiLopxeCau84, schema as AiLopxeCau84Schema} from './ai/lopxe_cau84.jsx';
const AiLopxeCau84G = coGiong(AiLopxeCau84, "nhan_y/giong_lopxe_cau84.wav");
import {Canh as AiLopxeCau85, schema as AiLopxeCau85Schema} from './ai/lopxe_cau85.jsx';
const AiLopxeCau85G = coGiong(AiLopxeCau85, "nhan_y/giong_lopxe_cau85.wav");
import {Canh as AiLopxeCau86, schema as AiLopxeCau86Schema} from './ai/lopxe_cau86.jsx';
const AiLopxeCau86G = coGiong(AiLopxeCau86, "nhan_y/giong_lopxe_cau86.wav");
import {Canh as AiLopxeCau87, schema as AiLopxeCau87Schema} from './ai/lopxe_cau87.jsx';
const AiLopxeCau87G = coGiong(AiLopxeCau87, "nhan_y/giong_lopxe_cau87.wav");
import {Canh as AiLopxeCau88, schema as AiLopxeCau88Schema} from './ai/lopxe_cau88.jsx';
const AiLopxeCau88G = coGiong(AiLopxeCau88, "nhan_y/giong_lopxe_cau88.wav");
import {Canh as AiLopxeCau89, schema as AiLopxeCau89Schema} from './ai/lopxe_cau89.jsx';
const AiLopxeCau89G = coGiong(AiLopxeCau89, "nhan_y/giong_lopxe_cau89.wav");
import {Canh as AiLopxeCau9, schema as AiLopxeCau9Schema} from './ai/lopxe_cau9.jsx';
const AiLopxeCau9G = coGiong(AiLopxeCau9, "nhan_y/giong_lopxe_cau9.wav");
import {Canh as AiLopxeCau90, schema as AiLopxeCau90Schema} from './ai/lopxe_cau90.jsx';
const AiLopxeCau90G = coGiong(AiLopxeCau90, "nhan_y/giong_lopxe_cau90.wav");
import {Canh as AiLopxeCau91, schema as AiLopxeCau91Schema} from './ai/lopxe_cau91.jsx';
const AiLopxeCau91G = coGiong(AiLopxeCau91, "nhan_y/giong_lopxe_cau91.wav");
import {Canh as AiLopxeCau92, schema as AiLopxeCau92Schema} from './ai/lopxe_cau92.jsx';
const AiLopxeCau92G = coGiong(AiLopxeCau92, "nhan_y/giong_lopxe_cau92.wav");
import {Canh as AiLopxeCau93, schema as AiLopxeCau93Schema} from './ai/lopxe_cau93.jsx';
const AiLopxeCau93G = coGiong(AiLopxeCau93, "nhan_y/giong_lopxe_cau93.wav");
import {Canh as AiLopxeCau94, schema as AiLopxeCau94Schema} from './ai/lopxe_cau94.jsx';
const AiLopxeCau94G = coGiong(AiLopxeCau94, "nhan_y/giong_lopxe_cau94.wav");
import {Canh as AiLopxeCau95, schema as AiLopxeCau95Schema} from './ai/lopxe_cau95.jsx';
const AiLopxeCau95G = coGiong(AiLopxeCau95, "nhan_y/giong_lopxe_cau95.wav");
import {Canh as AiLopxeCau96, schema as AiLopxeCau96Schema} from './ai/lopxe_cau96.jsx';
const AiLopxeCau96G = coGiong(AiLopxeCau96, "nhan_y/giong_lopxe_cau96.wav");
import {Canh as AiLopxeCau97, schema as AiLopxeCau97Schema} from './ai/lopxe_cau97.jsx';
const AiLopxeCau97G = coGiong(AiLopxeCau97, "nhan_y/giong_lopxe_cau97.wav");
import {Canh as AiLopxeCau98, schema as AiLopxeCau98Schema} from './ai/lopxe_cau98.jsx';
const AiLopxeCau98G = coGiong(AiLopxeCau98, "nhan_y/giong_lopxe_cau98.wav");
import {Canh as AiLopxeCau99, schema as AiLopxeCau99Schema} from './ai/lopxe_cau99.jsx';
const AiLopxeCau99G = coGiong(AiLopxeCau99, "nhan_y/giong_lopxe_cau99.wav");
// NHAN_Y_AI_IMPORT_KET_THUC

const FPS = 30;
// Thời lượng lấy từ props.giay (Python truyền theo độ dài giọng đọc của cảnh).
const meta = async ({props}: {props: any}) => ({
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
    <Composition id="NhanY" component={NhanY} width={1920} height={1080} fps={FPS}
      durationInFrames={150} defaultProps={{giay: 5, nen: '', anh: '', nhip: []}} calculateMetadata={meta} />
    <Composition id="NuocDang" component={NuocDang} width={1920} height={1080} fps={FPS}
      durationInFrames={240} schema={nuocDangSchema} defaultProps={NUOC_DANG_MAC_DINH} calculateMetadata={meta} />
    <Composition id="GiaiPhau" component={GiaiPhau} width={1920} height={1080} fps={FPS}
      durationInFrames={300} schema={giaiPhauSchema} defaultProps={GIAI_PHAU_MAC_DINH} calculateMetadata={meta} />
    <Folder name="sua-tay">
      {/* NHAN_Y_SUA_BAT_DAU — khối này do chinh_sua/nhan_y.py sinh ra: mỗi chỗ nhấn ý dựng bằng cảnh mẫu 3D là một mục.
          Sửa thông số ở bảng bên phải Studio rồi bấm lưu (Studio ghi vào đây); chạy lại nhan_y.py thì dựng đúng chỗ đã sửa. */}
      <Composition id="ai-caloc-cau106" component={AiCalocCau106G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau106Schema} calculateMetadata={meta}
        defaultProps={{"bgImage": "nhan_y/c971e66784d097.jpg", "salmonImage": "nhan_y/fd9acf07152889.png", "eelImage": "nhan_y/3d2e9d40089aa0.png", "larvaeImage": "nhan_y/268ba2971bedaf.png", "title1": "Bơi lội ở tầng nước giữa", "title2": "Đào bới sâu vào bùn cát", "giay": 10.47}} />
      <Composition id="ai-caloc-cau20" component={AiCalocCau20G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau20Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen_dia_hinh": "nhan_y/765df697ab6b6e.jpg", "anh_toa_nha": "nhan_y/de0cd8f6f058b1.png", "nhan_do_cao": "~99 m", "nhan_tang_nha": "30 tầng", "nhan_ho_erie": "HỒ ERIE", "nhan_ho_ontario": "HỒ ONTARIO", "mau_thuoc_do": "#00f0ff", "giay": 8.29}} />
      <Composition id="ai-caloc-cau33" component={AiCalocCau33G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau33Schema} calculateMetadata={meta}
        defaultProps={{"bgImage": "nhan_y/5fc4953aed5817.jpg", "boatImage": "nhan_y/3c7adf348cdc8a.png", "gateImage": "nhan_y/f278721193a171.png", "text1": "1. Khóa cổng", "text2": "2. Cân bằng mực nước", "text1From": 116, "text2From": 263, "waterRiseFrom": 174, "waterRiseTo": 263, "boatEnterFrom": 77, "boatEnterTo": 101, "lowWaterLevel": 680, "highWaterLevel": 440, "giay": 10.85}} />
      <Composition id="ai-caloc-cau53" component={AiCalocCau53G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau53Schema} calculateMetadata={meta}
        defaultProps={{"nenNguDaiHo": "nhan_y/2ae05ac64e2f9c.jpg", "tachCaHoi": "nhan_y/cd2e783a4e3d55.png", "canMiengBamThit": "nhan_y/0bc3cf831df4fd.jpg", "nhanChatChongDong": "CHẤT CHỐNG ĐÔNG MÁU", "nhanThoiGian": "1 - 1,5 NĂM", "kichThuocNhan": 58, "mauLamellipodin": "rgba(200, 100, 255, 0.85)", "mauMauTuoi": "#e01616", "giay": 10.91}} />
      <Composition id="ai-caloc-cau57" component={AiCalocCau57G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau57Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/3f0493e82d2ae2.jpg", "anh_au_trung": "nhan_y/653af02f9937df.png", "tieu_de_an_minh": "Ẩn mình • Mù lòa", "tieu_de_thoi_gian": "3 – 10+", "don_vi_thoi_gian": "NĂM", "giay": 7.27}} />
      <Composition id="ai-caloc-cau64" component={AiCalocCau64G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau64Schema} calculateMetadata={meta}
        defaultProps={{"mapBgPath": "nhan_y/1229a8e2d2d1b8.jpg", "redArrowPath": "nhan_y/afd8fed24df4d0.png", "tieudeBeat1": "1937: Hồ Huron", "tieudeBeat2": "1938: Hồ Superior", "tieudeBeat3": "Hoàn tất xâm chiếm Ngũ Hồ", "mauDoMuc": "#9a1818", "mauGiayDa": "#f5ebd5", "mauChuDam": "#24180e", "giay": 10.23}} />
      <Composition id="ai-caloc-cau73" component={AiCalocCau73G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau73Schema} calculateMetadata={meta}
        defaultProps={{"bgNen": "nhan_y/e97c2ea126ad38.jpg", "bgCanThung": "nhan_y/e29c7cdd7efeb8.jpg", "imgXeTai": "nhan_y/bfccd7fb86b0d3.png", "text1": "340 xe (gần 7.000 tấn)", "text2": "7 xe (135 tấn - 2%)", "text1Color": "#facc15", "text2Color": "#ef4444", "textSize": 90, "xeWidth": 140, "xeHeight": 67, "giay": 10.45}} />
      <Composition id="ai-caloc-cau87" component={AiCalocCau87G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau87Schema} calculateMetadata={meta}
        defaultProps={{"nenSuoi": "nhan_y/3cecf0562930bc.jpg", "anhDapTran": "nhan_y/75ec4266c02b36.png", "anhCaMutDa": "nhan_y/595f958eb600fc.png", "anhCaBanDia": "nhan_y/8f3a37d386c022.png", "tieuDePhacThao": "THIẾT KẾ ĐẬP TRÀN BẢO VỆ", "nhanDoCao": "Chênh lệch độ cao vừa phải", "nhanChanCaMutDa": "BỊ CHẶN LẠI & TRÔI XUỐNG", "nhanCaBanDiaNhay": "CÁ BẢN ĐỊA NHẢY QUA DỄ DÀNG", "nhanCuaDan": "CỬA DẪN RIÊNG BIỆT (FISHWAY)", "giay": 13.21}} />
      <Composition id="ai-caloc-cau99" component={AiCalocCau99G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiCalocCau99Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen_song": "nhan_y/c2b5ed2c53e063.jpg", "anh_au_trung": "nhan_y/ca785beaee76c2.png", "anh_ca_hoi_van": "nhan_y/5d8346e097582c.png", "anh_ca_tue": "nhan_y/ad060c4317b359.png", "tieu_de_ca_hoi": "50% Cá hồi vân", "tieu_de_ca_tue": "40% Cá tuế đầu to", "mau_hoa_chat": "#f59e0b", "mau_nguy_hiem": "#ef4444", "giay": 8.43}} />
      <Composition id="ai-lopxe-cau1" component={AiLopxeCau1G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau1Schema} calculateMetadata={meta}
        defaultProps={{"anhSaMac": "nhan_y/058f2cf77a78e4.jpg", "anhLongSuoi": "nhan_y/f10d1354ea814f.jpg", "anhBaiLop": "nhan_y/a2d909cf7235bc.jpg", "anhCumLop": "nhan_y/34e7cf3c477993.png", "soLop": 1500, "coSoDem": 150, "giayDem": 3.2, "doToiSaMac": 0.08, "doToiLongSuoi": 0.12, "doToiBaiLop": 0.14, "doDamBui": 0.62, "giay": 9.36}} />
      <Composition id="ai-lopxe-cau10" component={AiLopxeCau10G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau10Schema} calculateMetadata={meta}
        defaultProps={{"bgImage": "nhan_y/7ea55b730055a5.jpg", "cowImage": "nhan_y/78f727ccdc1ef8.png", "title1": "40.000 con bò", "title2": "1.500.000 con bò (Quá tải)", "giay": 9.44}} />
      <Composition id="ai-lopxe-cau100" component={AiLopxeCau100G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau100Schema} calculateMetadata={meta}
        defaultProps={{"anhLop": "nhan_y/43efc22565f2ce.jpg", "anhRan": "nhan_y/a128212c495589.jpg", "tieuDe": "FLORIDA", "coTieuDe": 150, "mauMuiTen": "#FFD400", "mauVong": "#FFFFFF", "netMuiTen": 16, "toiLop": 0.22, "toiRan": 0.18, "zoomLop": 1.14, "zoomRan": 1.06, "giay": 10.07}} />
      <Composition id="ai-lopxe-cau101" component={AiLopxeCau101G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau101Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/ed31998679f14d.jpg", "anhCan": "nhan_y/c4581493a70f14.jpg", "soTrieu": "1.000.000 – 2.000.000", "doSau": 20, "giayDem": 4.6, "coSoTrieu": 104, "coDoSau": 150, "mauChu": "#F2EAD8", "doToiNen": 0.3, "doToiCan": 0.12, "giay": 8.87}} />
      <Composition id="ai-lopxe-cau102" component={AiLopxeCau102G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau102Schema} calculateMetadata={meta}
        defaultProps={{"anhToanCanh": "nhan_y/a985160934000e.jpg", "anhTrungCanh": "nhan_y/c3c8e7661f8172.jpg", "anhMacro": "nhan_y/d97764b45286c0.jpg", "chuChinh": "Osborne", "coChu": 150, "mauNhan": "#FFD400", "doDaiGach": 660, "toiAnh1": 0.18, "toiAnh2": 0.15, "toiAnh3": 0.12, "daiChuyen": 16, "quangPan": 140, "giay": 11.0}} />
      <Composition id="ai-lopxe-cau103" component={AiLopxeCau103G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau103Schema} calculateMetadata={meta}
        defaultProps={{"title1": "1-2 triệu lốp xe", "title2": "Nhấn chìm 20m dưới biển", "title3": "Khóa thép", "image1": "nhan_y/fb02a4353e2e57.jpg", "image2": "nhan_y/4a6a5b97afef87.jpg", "image3": "nhan_y/64e7736fa96150.jpg", "giay": 8.35}} />
      <Composition id="ai-lopxe-cau104" component={AiLopxeCau104G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau104Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/a0ba6fe1be6a14.jpg", "anhKhoa": "nhan_y/4fb9edfe67da5d.jpg", "anhDay": "nhan_y/22e984ea29224b.jpg", "anhNuoc": "nhan_y/826225c50a38f7.jpg", "anhNhomTach": "nhan_y/b5342fdb6fdcdc.png", "anhLopTroi": "nhan_y/02c3bfea7c886e.png", "doPhongNen": 1.16, "doPhongDay": 1.12, "doPhongNuoc": 1.3, "doMoNuoc": 0.78, "bienDoRung": 7, "doTachNhom": 380, "doTroiLop": 130, "giay": 10.55}} />
      <Composition id="ai-lopxe-cau105" component={AiLopxeCau105G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau105Schema} calculateMetadata={meta}
        defaultProps={{"anhDayBien": "nhan_y/f38733f12c128a.jpg", "anhSanHo": "nhan_y/cba6daa3e04697.jpg", "anhBaiBien": "nhan_y/788b3e2fdcc3cf.jpg", "soLuong": 1000000, "donVi": "lốp xe", "coSo": 120, "giayDem": 2.6, "panNgang": 160, "daiWipe": 12, "daiTruot": 16, "toiDayBien": 0.2, "toiSanHo": 0.14, "toiBaiBien": 0.12, "giay": 9.41}} />
      <Composition id="ai-lopxe-cau106" component={AiLopxeCau106G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau106Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/6f00009f5a7e3c.jpg", "soLuong": 1600, "coSo": 210, "mauSo": "#FFFFFF", "mauVang": "#F5C242", "toiNen": 0.32, "giay": 8.35}} />
      <Composition id="ai-lopxe-cau107" component={AiLopxeCau107G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau107Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/f28737a0b30450.jpg", "anhThoLan": "nhan_y/359a46655cf4b3.jpg", "nam": "2007 – 2009", "soLop": 72000, "coNam": 132, "coSo": 240, "mauVang": "#f5c542", "mauChu": "#ffffff", "doToi": 0.28, "heSoZoomNen": 1.12, "thoiGianDem": 30, "doTreVong": 6, "giay": 10.93}} />
      <Composition id="ai-lopxe-cau108" component={AiLopxeCau108G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau108Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/12d9f3bce7169f.jpg", "anhLop": "nhan_y/d43f2e72a0ee24.jpg", "namDau": "2023", "soLop": "640.000", "namCuoi": "2030", "mauChinh": "#F7F2E4", "mauNhan": "#FFC53D", "coSoLon": 230, "coNam": 132, "doToi": 0.42, "rongKhung": 560, "caoKhung": 352, "giay": 12.79}} />
      <Composition id="ai-lopxe-cau109" component={AiLopxeCau109G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau109Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/fe04322ec794b5.jpg", "zoomTu": 1.02, "zoomDen": 1.12, "doToi": 0.18, "mauNet": "#8fe8ff", "mauNhan": "#4fd0e8", "frameGay": 175, "doGay": 18, "giay": 13.54}} />
      <Composition id="ai-lopxe-cau11" component={AiLopxeCau11G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau11Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/9f4a7868b7d071.jpg", "anhBo": "nhan_y/96a3f46979d67b.png", "soDau": 120, "soCuoi": 1500000, "donVi": "con", "khungBatDau": 0, "khungNhay": 20, "soFrameNhay": 60, "khungBo": 0, "xDem": 120, "yDem": 110, "coDem": 96, "mauDem": "#FFFFFF", "mauDonVi": "#FFD166", "xCot": 1700, "yCot": 680, "rongCot": 90, "khoangCot": 40, "caoCot1": 90, "caoCot2": 380, "mauCot1": "#8FB8DE", "mauCot2": "#FFD166", "xBo": 900, "yBo": 260, "rongBo": 700, "giay": 4.81}} />
      <Composition id="ai-lopxe-cau110" component={AiLopxeCau110G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau110Schema} calculateMetadata={meta}
        defaultProps={{"bgImage1": "https://images.unsplash.com/photo-1524661135-423995f22d0b?q=80&w=1920&auto=format&fit=crop", "bgImage2": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?q=80&w=1920&auto=format&fit=crop", "yearText": "2007 - 2009", "counterUnit": "chiếc lốp", "giay": 10.43}} />
      <Composition id="ai-lopxe-cau111" component={AiLopxeCau111G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau111Schema} calculateMetadata={meta}
        defaultProps={{"anhToanCanh": "nhan_y/cb3a85b889311c.jpg", "anhBanDo": "nhan_y/82525a06299d50.jpg", "anhLopXe": "nhan_y/14701547c1da9f.jpg", "anhThanhThep": "nhan_y/c0a650042cf4f8.jpg", "anhCatLop": "nhan_y/ca759394deec3f.jpg", "anhLuQuet": "nhan_y/c6038d1de70528.jpg", "chuChinh": "BRAWLEY WASH", "coChu": 128, "mauChu": "#ffffff", "mauGach": "#FFC400", "mauNet": "#ffffff", "doDayNet": 7, "rongGachChan": 920, "zoomNhe": 1.04, "zoomManh": 1.18, "quangPan": 70, "doToi": 0.08, "giay": 14.0}} />
      <Composition id="ai-lopxe-cau112" component={AiLopxeCau112G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau112Schema} calculateMetadata={meta}
        defaultProps={{"anhFlorida": "nhan_y/845da9f0cbd4b3.jpg", "anhArizona": "nhan_y/4263035b30b69d.jpg", "anhThep": "nhan_y/758cde58b36ae2.jpg", "chuFlorida": "Florida", "chuArizona": "Arizona", "coChu": 150, "mauChu": "#FFFFFF", "mauGach": "#FFC400", "toiFlorida": 0.18, "toiArizona": 0.05, "zoomFloridaTu": 1.28, "zoomFloridaDen": 1.0, "zoomArizonaTu": 1.02, "zoomArizonaDen": 1.18, "zoomThepTu": 1.3, "zoomThepDen": 1.0, "rongKhungThep": 880, "caoKhungThep": 560, "giay": 8.51}} />
      <Composition id="ai-lopxe-cau113" component={AiLopxeCau113G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau113Schema} calculateMetadata={meta}
        defaultProps={{"anhBao": "nhan_y/799abee5fb91bb.jpg", "anhSaMac": "nhan_y/0128b328d57f0e.jpg", "anhChongLop": "nhan_y/765a37ce70911e.png", "fBao": 4, "fTruot": 107, "fDongBang": 177, "fCham": 194, "thoiLuong": 274, "quangBao": 90, "phongBao": 1.12, "toiBao": 0.12, "toiSaMac": 0.08, "xLop": 580, "yLop": 190, "wLop": 760, "hLop": 734, "doTruot": 1500, "doBang": 0.16, "doTruotNen": 0.05, "doBangMo": 0.62, "doVang": 0.5, "giay": 9.13}} />
      <Composition id="ai-lopxe-cau114" component={AiLopxeCau114G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau114Schema} calculateMetadata={meta}
        defaultProps={{"anhLopXe": "nhan_y/52f849297c26df.jpg", "anhDat": "nhan_y/737a10e9d30a00.jpg", "anhBeTong": "nhan_y/b29dabda69d071.jpg", "soLuong": 1500, "donVi": "", "demGiay": 1.1, "coSo": 200, "wipeDat": 22, "wipeBeTong": 10, "giay": 12.35}} />
      <Composition id="ai-lopxe-cau115" component={AiLopxeCau115G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau115Schema} calculateMetadata={meta}
        defaultProps={{"suoiTuNhienPath": "nhan_y/2637d34689aead.jpg", "reCayPath": "nhan_y/71fc59f63bff35.png", "datKhoNutNePath": "nhan_y/c6275831f957be.jpg", "tuNghienTitle": "DÒNG CHẢY TỰ NHIÊN", "cangThangTitle": "PHẢN ỨNG CỨNG NHẮC", "giay": 13.32}} />
      <Composition id="ai-lopxe-cau116" component={AiLopxeCau116G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau116Schema} calculateMetadata={meta}
        defaultProps={{"nen1": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09", "can1": "https://images.unsplash.com/photo-1578632767115-351597cf2477", "tieuDeKhoa": "BỊ ĐÓNG BĂNG SUỐT NHIỀU NĂM", "mauBang": "#38bdf8", "giay": 7.51}} />
      <Composition id="ai-lopxe-cau117" component={AiLopxeCau117G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau117Schema} calculateMetadata={meta}
        defaultProps={{"anhNuoc": "nhan_y/efee9c2c3835b2.jpg", "anhRe": "nhan_y/c9b8e8b97f8547.jpg", "anhNhanh": "nhan_y/6a5390aa98eb2a.png", "panNuoc": 90, "phongNuoc": 1.1, "toiNuoc": 0.12, "driftNgang": 14, "driftDoc": -20, "zoomReTu": 1.02, "zoomReDen": 1.1, "toiRe": 0.1, "punch": 0.1, "sweepMau": "rgba(255,255,255,0.55)", "sweepRong": 45, "sweepDay": 20, "nhanhLech": 900, "nhanhNghieng": 1.4, "nhanhNhup": 6, "nhanhMo": 1, "giay": 6.79}} />
      <Composition id="ai-lopxe-cau118" component={AiLopxeCau118G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau118Schema} calculateMetadata={meta}
        defaultProps={{"anh_ban_lam_viec": "nhan_y/82d13269c3e9b5.jpg", "anh_tai_lieu": "nhan_y/78e198f264e2ec.jpg", "anh_cua_so": "nhan_y/a633118a69c183.jpg", "quang_truot_ban": 70, "toi_ban_lam_viec": 0.18, "phong_cua_so_tu": 1.16, "phong_cua_so_den": 1.0, "the_toc_do": 95, "the_nghieng": -1.6, "the_le_tren": 666, "mau_nhan": "#E8B23A", "giay": 10.79}} />
      <Composition id="ai-lopxe-cau119" component={AiLopxeCau119G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau119Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/126033d7cbfb9c.jpg", "anhNguoi": "nhan_y/16440bc7de4129.png", "anhNgoc": "nhan_y/3921638465ecbc.jpg", "anhKim": "nhan_y/fa4a49924bd162.png", "anhNuoc": "nhan_y/941520a2351332.jpg", "toiNen": 0.18, "dayNen": 1.1, "punch": 1.12, "sweepRong": 520, "giay": 5.03}} />
      <Composition id="ai-lopxe-cau12" component={AiLopxeCau12G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau12Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/5b1bf3afe50800.jpg", "anh_mong": "nhan_y/c289cd70275f30.png", "anh_bua": "nhan_y/e9cd8b7594e7ad.png", "anh_dat": "nhan_y/ea71cd584eb5c5.jpg", "anh_thuc_vat": "nhan_y/a86af74eb4bc31.png", "luc_punch": 0.055, "nhip_mong": 9, "do_nhay_mong": 92, "toc_do_truot": 0.28, "rong_mong": 500, "rong_bua": 1120, "rong_thuc_vat": 1500, "giay": 10.63}} />
      <Composition id="ai-lopxe-cau120" component={AiLopxeCau120G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau120Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/a93d739deca7c3.jpg", "zoomTu": 1.02, "zoomDen": 1.13, "gocZoom": "50% 46%", "toiNen": 0.16, "chuKhoa": "chậm lại", "coChuKhoa": 150, "mauChuKhoa": "#FFF8EC", "mauGachChan": "#FFC53D", "chuX": 150, "chuY": 700, "mauNhip": "#FF5A4E", "rongNhip": 520, "caoNhip": 170, "nhipX": 1330, "nhipY": 120, "tocDoTruot": 520, "doDamNhip": 6, "giay": 9.95}} />
      <Composition id="ai-lopxe-cau121" component={AiLopxeCau121G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau121Schema} calculateMetadata={meta}
        defaultProps={{"anhBinhLuan": "nhan_y/6a5390aa98eb2a.png", "anhNutDangKy": "nhan_y/db2ea33998c20a.png", "anhHaoQuang": "nhan_y/bd45fa7b3e8063.png", "anhTheVideo": "nhan_y/6d1b521341a57f.png", "mauNenTren": "#1b1740", "mauNenDuoi": "#0d0b1e", "rongTheBinhLuan": 1000, "rongNutDangKy": 900, "rongHaoQuang": 1240, "rongTheVideo": 560, "doToi": 0.42, "giay": 11.15}} />
      <Composition id="ai-lopxe-cau13" component={AiLopxeCau13G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau13Schema} calculateMetadata={meta}
        defaultProps={{"anh1": "nhan_y/519a4ce60ef768.jpg", "anh2": "nhan_y/6f8549424b7742.jpg", "anh3": "nhan_y/e95cabf3df153d.jpg", "toi1": 0.06, "toi2": 0.18, "toi3": 0.12, "soLo": 18, "mauLo": "#8fe6ff", "doMoLo": 0.55, "soHatMua": 130, "mauMua": "#dfeaff", "gocMua": 0.24, "doDaiTruot": 16, "giay": 10.45}} />
      <Composition id="ai-lopxe-cau14" component={AiLopxeCau14G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau14Schema} calculateMetadata={meta}
        defaultProps={{"anhNen1": "nhan_y/b8fb421a55f414.jpg", "anhDatSut": "nhan_y/9c923096b53155.png", "anhNen2": "nhan_y/9cb2280e034ad6.jpg", "mauDuong": "#FFA51E", "dayNet": 7, "quangTruotNgang": 200, "quangTruotDoc": 250, "rongDat": 640, "caoDat": 674, "toiNen1": 0.08, "toiNen2": 0.07, "giay": 5.51}} />
      <Composition id="ai-lopxe-cau15" component={AiLopxeCau15G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau15Schema} calculateMetadata={meta}
        defaultProps={{"anhBanDo": "nhan_y/a8a1331b37f2a2.jpg", "anhKenh": "nhan_y/0a079ef0693203.jpg", "anhVuc": "nhan_y/06574f14c63041.png", "anhNha": "nhan_y/3719ed9ffb695c.jpg", "tenSong1": "Santa Cruz", "mauDuong": "#f0b429", "mauNhan": "#ffffff", "coNhan": 34, "dayNet": 6, "zoomNenTu": 1.04, "zoomNenDen": 1.2, "zoomNhaTu": 1, "zoomNhaDen": 1.14, "doMoNen": 0.55, "giay": 12.75}} />
      <Composition id="ai-lopxe-cau16" component={AiLopxeCau16G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau16Schema} calculateMetadata={meta}
        defaultProps={{"anh_trang_trai": "nhan_y/d0a202b82990d6.jpg", "anh_bien_hieu": "nhan_y/c364bf28dd3003.png", "anh_can_ranh_xoi": "nhan_y/97bc1b73af8e78.jpg", "anh_nha_trang_trai": "nhan_y/c80ffeed16a9ca.png", "mau_net_do": "#e8231c", "day_net_do": 14, "rong_bien_hieu": 900, "rong_nha": 880, "do_toi_nen": 0.12, "quang_pan": 90, "zoom_dau": 1.03, "zoom_cuoi": 1.13, "giay": 4.89}} />
      <Composition id="ai-lopxe-cau17" component={AiLopxeCau17G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau17Schema} calculateMetadata={meta}
        defaultProps={{"anh1895": "nhan_y/9c25fcb50009b8.jpg", "anhAltar": "nhan_y/ba410c78610916.jpg", "anhDC": "nhan_y/08846cc58f4f10.png", "nam": "1895", "soHa": 17700, "donVi": "ha", "mauVang": "#E8C15A", "mauVien": "#E0332B", "coChuNam": 200, "coDem": 132, "rongDC": 560, "giay": 11.11}} />
      <Composition id="ai-lopxe-cau18" component={AiLopxeCau18G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau18Schema} calculateMetadata={meta}
        defaultProps={{"anhNenTrangTrai": "nhan_y/68922166b280f1.jpg", "anhNenLuBun": "nhan_y/f62b47f62aa256.jpg", "anhCanDuongCat": "nhan_y/ba57f867852c6b.jpg", "anhDanBo": "nhan_y/77dceb1712be98.png", "anhTheHe": "nhan_y/08846cc58f4f10.png", "chuKhoa": "5 THẾ HỆ", "coChu": 150, "mauChu": "#FFF7E2", "doDamNen": 0.06, "doDamLu": 0.04, "punchNen": 1.1, "punchDuong": 1.26, "giay": 12.64}} />
      <Composition id="ai-lopxe-cau19" component={AiLopxeCau19G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau19Schema} calculateMetadata={meta}
        defaultProps={{"tieuDe": "THẾ HỆ NHÀ KING", "namKhoiDau": "1895", "namKetThuc": "1980s", "dienTichSo": 17700, "dienTichDonVi": "HÉC TA", "anhNen1": "nhan_y/9daa6825e598c6.jpg", "anhDanBo": "nhan_y/d6c11a245eb961.png", "anhDatToTien": "nhan_y/130c592e849aa3.jpg", "giay": 5.33}} />
      <Composition id="ai-lopxe-cau2" component={AiLopxeCau2G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau2Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/6ce6cffb8bbfba.jpg", "anh_nong_dan": "nhan_y/7adca85fe49118.png", "chu_doan_1": "Không ai tin", "chu_doan_2": "Tạo nên trò trống gì?", "nhan_so_lop": "1.500 LỐP PHẾ LIỆU", "giay": 3}} />
      <Composition id="ai-lopxe-cau20" component={AiLopxeCau20G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau20Schema} calculateMetadata={meta}
        defaultProps={{"anhNen1": "nhan_y/cd2c719e2b2e4d.jpg", "anhJohn": "nhan_y/c22221f3f1eae7.png", "anhMayUi": "nhan_y/4ae87635091f4c.png", "anhNen2": "nhan_y/e6332335a67a92.jpg", "anhXucTuyet": "nhan_y/0fa32f5286dba4.jpg", "johnLeft": 1318, "johnTop": 262, "johnHeight": 818, "mayUiLeft": 430, "mayUiTop": 556, "mayUiWidth": 880, "whipStart": 206, "whipDur": 16, "nen1ZoomTu": 1.04, "nen1ZoomDen": 1.18, "nen2ZoomTu": 1.06, "nen2ZoomDen": 1.16, "uiDay": 200, "xucPunch": 1.32, "toiNen1": 0.12, "toiNen2": 0.1, "giay": 12.57}} />
      <Composition id="ai-lopxe-cau21" component={AiLopxeCau21G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau21Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/5f24098f1c05f5.jpg", "anhDap": "nhan_y/b86b7a1e78fc55.png", "tongTien": 70000, "nguongDo": 45000, "coSo": 150, "rongThanh": 800, "mauSo": "#f5f7fa", "mauDo": "#ff3b30", "mauDay": "#3ddc84", "damTrai": 240, "damTren": 480, "damRong": 700, "giay": 12.79}} />
      <Composition id="ai-lopxe-cau22" component={AiLopxeCau22G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau22Schema} calculateMetadata={meta}
        defaultProps={{"anhPhongLamViec": "nhan_y/abd85f4ab0fa38.jpg", "anhBanDo": "nhan_y/6bdf38ecb7d895.jpg", "anhNhanVat": "nhan_y/bf297738030ad4.png", "anhBangCap": "nhan_y/c59c1941a71fdd.jpg", "namMoc": "1996", "coNam": 170, "mauVach": "#d02a1e", "doDamVach": 9, "soVach": 9, "coNhanVat": 750, "viTriNhanVat": 1200, "coBangCap": 700, "doToiNen": 0.45, "giay": 14.0}} />
      <Composition id="ai-lopxe-cau23" component={AiLopxeCau23G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau23Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/466ba10d6d6d69.jpg", "anh_the": "nhan_y/1fb662dc2f9fa6.jpg", "chu_nut": "ĐĂNG KÝ", "mau_nut": "#F5C542", "mau_chu_nut": "#17171C", "mau_vien_the": "rgba(255,255,255,0.55)", "mau_nhan": "#F5C542", "mau_chuong": "#F5C542", "mau_nen_chuong": "#1B1B22", "zoom_nen_tu": 1.16, "zoom_nen_den": 1.0, "toi_nen": 0.18, "do_toi_beat3": 0.4, "rong_the_dau": 640, "rong_the_giua": 980, "rong_preview": 1460, "giay": 8.87}} />
      <Composition id="ai-lopxe-cau24" component={AiLopxeCau24G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau24Schema} calculateMetadata={meta}
        defaultProps={{"anh_nguoi_linh": "nhan_y/8e3a33bb6678cf.jpg", "huy_hieu": "nhan_y/dd4d4943a7f69c.png", "anh_berkeley": "nhan_y/b023482987f932.jpg", "bang_tien_si": "nhan_y/34315c281ff5bf.png", "anh_lab": "nhan_y/0314ca76dce307.jpg", "anh_vi_mach": "nhan_y/66db54e2bb1dda.jpg", "chu_berkeley": "Berkeley", "chu_tucson": "Tucson", "so_bang_sang_che": 7, "co_chu_berkeley": 150, "co_chu_tucson": 130, "co_so_7": 560, "mau_vang": "#f3c33f", "do_toi_nen": 0.45, "giay": 11.73}} />
      <Composition id="ai-lopxe-cau25" component={AiLopxeCau25G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau25Schema} calculateMetadata={meta}
        defaultProps={{"anhSuoi": "nhan_y/d4c37c2cbe3e34.jpg", "anhBieuDo": "nhan_y/fe6e88ef6c8ef2.jpg", "anhTrangTrai": "nhan_y/8545df8f1a9c8c.jpg", "anhLopXe": "nhan_y/32e9e90c2f83cb.jpg", "zoomSuoiTu": 1.02, "zoomSuoiDen": 1.14, "zoomBieuDoTu": 1.04, "zoomBieuDoDen": 1.15, "zoomTrangTraiTu": 1.08, "zoomTrangTraiDen": 1.18, "zoomLopXeTu": 1.24, "zoomLopXeDen": 1.08, "quangTruotNgang": 1920, "soFrameTruotNgang": 18, "quangTruotDoc": 1080, "soFrameTruotDoc": 20, "soFrameHienLopXe": 14, "toiSuoi": 0.1, "toiBieuDo": 0.18, "toiTrangTrai": 0.08, "toiLopXe": 0.14, "giay": 12.6}} />
      <Composition id="ai-lopxe-cau26" component={AiLopxeCau26G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau26Schema} calculateMetadata={meta}
        defaultProps={{"phongKyThuatPath": "nhan_y/081a9061c527c8.jpg", "dongSongThuyVanPath": "nhan_y/181f731996adcd.jpg", "tu_Scale": 1, "den_Scale": 1.05, "tu_Scale_ThuyVan": 1.02, "den_Scale_ThuyVan": 1.07, "pan_X_Max": 40, "punchInPercentage": 12, "punchInStartFrame": 76, "lightSweepStartFrame": 76, "sweepWidth": 400, "sweepColor": "rgba(255, 255, 255, 0.8)", "stiffness_Slide": 120, "damping_Slide": 20, "stiffness_Punch": 180, "damping_Punch": 15, "giay": 3.73}} />
      <Composition id="ai-lopxe-cau27" component={AiLopxeCau27G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau27Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/2a8b9bdf9067ac.jpg", "anhLop": "nhan_y/f65bcab379efcd.png", "soLuong": 242000000, "phanTram": 9, "coSo": 250, "coNhan": 96, "mauSo": "#FFC72C", "mauThanh": "#FF6A2B", "rongLop": 1100, "giay": 10.44}} />
      <Composition id="ai-lopxe-cau29" component={AiLopxeCau29G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau29Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/ff7e31bdc51fa7.jpg", "nhan1990": "1990s", "soLuong": 242000000, "donVi": "chiếc lốp/năm", "giayDem": 2.4, "coSoDem": 150, "chuTyLe": "< 10%", "coChuTyLe": 132, "mauDo": "#B5453C", "mauVong": "rgba(255,255,255,0.30)", "banKinh": 290, "tyLe": 0.1, "doDam": 0.28, "quangPan": 90, "phongNen": 1.12, "giay": 10.05}} />
      <Composition id="ai-lopxe-cau3" component={AiLopxeCau3G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau3Schema} calculateMetadata={meta}
        defaultProps={{"anhLop": "nhan_y/994fb4a86520ba.jpg", "anhBan": "nhan_y/786c98819bbcfe.jpg", "mauNetCat": "#ffffff", "doDamNet": 4, "mauTem": "#c8102e", "chuTem": "UNRESOLVED", "coChuTem": 110, "gocTem": -9, "doMoAnh": 0.1, "giay": 9.09}} />
      <Composition id="ai-lopxe-cau30" component={AiLopxeCau30G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau30Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen_dat": "nhan_y/453e710fb6a079.jpg", "anh_lop_co": "nhan_y/05e4efc8a0f56b.png", "anh_thap_lop": "nhan_y/2437ed989229f5.png", "anh_bai_phe_lieu": "nhan_y/cb123d100504b4.jpg", "anh_can_muoi": "nhan_y/3455e04f2ac255.jpg", "anh_can_hoa_hoan": "nhan_y/0883692a4967b3.jpg", "phong_lop": 1.2, "phong_thap": 1.15, "phong_lua": 1.15, "giay": 10.79}} />
      <Composition id="ai-lopxe-cau31" component={AiLopxeCau31G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau31Schema} calculateMetadata={meta}
        defaultProps={{"anhToanCanh": "nhan_y/efcda5c96baa1f.jpg", "anhBaoCu": "nhan_y/a52aa1d0626be5.jpg", "anhKhoiDen": "nhan_y/99810fe6227e97.jpg", "chuHalloween": "ĐÊM HALLOWEEN 1983", "coChuLon": 152, "coSoNam": 214, "toiNen": 0.12, "nhanBanDo": "Winchester", "coNhanBanDo": 56, "giay": 7.53}} />
      <Composition id="ai-lopxe-cau32" component={AiLopxeCau32G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau32Schema} calculateMetadata={meta}
        defaultProps={{"anh_bai_lop": "nhan_y/674ac73b346a72.jpg", "anh_khoi": "nhan_y/ff2d0639230e7c.jpg", "anh_long_dat": "nhan_y/9eee37b100d6f9.jpg", "so_lop": 7000000, "counter_co": 150, "counter_giay": 3, "mau_chu": "#ffffff", "co_nhan_bang": 56, "mau_bien_gioi": "rgba(255,255,255,0.85)", "mau_tang_nuoc": "#2f8fc4", "mau_dau": "#0b0a09", "giay": 11.35}} />
      <Composition id="ai-lopxe-cau33" component={AiLopxeCau33G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau33Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/64afb5bae0fd75.jpg", "anhHazmat": "nhan_y/6dbee14d24bb31.jpg", "anhDau": "nhan_y/3ff5e4dffc7495.png", "chuDau": "SUPERFUND", "namBatDau": 1983, "namKetThuc": 2002, "coNam": 96, "mauNamDau": "#ffffff", "mauNamCuoi": "#ffcf3f", "doDamNen": 0.18, "rongKhungAnh": 760, "caoKhungAnh": 520, "giay": 7.23, "soNam": 20, "nhanNam": "NĂM"}} />
      <Composition id="ai-lopxe-cau34" component={AiLopxeCau34G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau34Schema} calculateMetadata={meta}
        defaultProps={{"anhTrangTrai": "nhan_y/5d27be704ad8a4.jpg", "anhVucXoiMon": "nhan_y/2499bddb18e79d.jpg", "anhNhaHoang": "nhan_y/cdc183563cd062.jpg", "anhDatNut": "nhan_y/59c3fa2f5453c0.jpg", "chuNam": "1995", "coNam": 168, "mauNam": "#F5EFE2", "viTriX": 110, "viTriY": 96, "mucPhongTo": 0.14, "doToiCuoi": 0.3, "doDamNen": 0.06, "giay": 12.41}} />
      <Composition id="ai-lopxe-cau35" component={AiLopxeCau35G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau35Schema} calculateMetadata={meta}
        defaultProps={{"anhKho": "nhan_y/921742e80d374d.jpg", "anhManh": "nhan_y/ee722ac78fa816.png", "anhDap": "nhan_y/6074ddaa9067e4.jpg", "tuKho": 1, "denKho": 1.12, "toiKho": 0.28, "rongManhA": 620, "rongManhB": 520, "tuDap": 1.12, "denDap": 1, "doMoDap": 1, "giay": 6.47}} />
      <Composition id="ai-lopxe-cau36" component={AiLopxeCau36G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau36Schema} calculateMetadata={meta}
        defaultProps={{"anhDam": "nhan_y/83295c48755490.jpg", "anhTuong": "nhan_y/a0528a4a01606f.jpg", "anhSoDo": "nhan_y/b7c42fb362a91a.png", "anhXuong": "nhan_y/c055d5598a03ff.jpg", "anhHonig": "nhan_y/3e7a7752fe81b6.png", "tenNhanVat": "HONIG", "coTen": 150, "mauTen": "#F5C518", "quangPanDam": 180, "phongDam": 1.06, "toiDam": 0.15, "tuTuong": 1.14, "denTuong": 1.0, "toiTuong": 0.24, "xSoDo": 1000, "ySoDo": 300, "rongSoDo": 860, "tuXuong": 1.0, "denXuong": 1.12, "toiXuong": 0.2, "xHonig": 960, "yHonig": 120, "rongHonig": 880, "giay": 13.38}} />
      <Composition id="ai-lopxe-cau37" component={AiLopxeCau37G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau37Schema} calculateMetadata={meta}
        defaultProps={{"tireDamBg": "nhan_y/cff5b14bc459e1.jpg", "tirePileImg": "nhan_y/544e02ca927dff.png", "concreteWallImg": "nhan_y/9f2f3225b52ca4.png", "blueprintDeskBg": "nhan_y/3f8825d2107248.jpg", "titleText": "Câu hỏi rất tự nhiên", "splitText": "Rác thải vs Bê tông", "finalText": "Vị thế người giải quyết", "giay": 12.8}} />
      <Composition id="ai-lopxe-cau38" component={AiLopxeCau38G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau38Schema} calculateMetadata={meta}
        defaultProps={{"anhDap": "nhan_y/a84ae9ba28cc91.jpg", "anhMach": "nhan_y/40c387dcccf0c0.jpg", "anhSuoi": "nhan_y/55dcaa11ecf372.jpg", "zoomDapTu": 1, "zoomDapDen": 1.12, "zoomSuoiTu": 1.18, "zoomSuoiDen": 1.02, "giayMo": 0.86, "doToiDap": 0.12, "giay": 8.33}} />
      <Composition id="ai-lopxe-cau39" component={AiLopxeCau39G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau39Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/7fae402ac98fa7.jpg", "anhTuong": "nhan_y/df2f44a0f8ed95.png", "anhCotThep": "nhan_y/ec12774cf34c9c.jpg", "zoomNenDau": 1.04, "zoomNenCuoi": 1.14, "toiNen": 0.35, "fTuong": 80, "fCotThep": 12, "fMuiTen": 242, "xTuong": 1040, "yTuong": 300, "wTuong": 780, "hTuong": 541, "xThe": 80, "yThe": 660, "wThe": 640, "hThe": 360, "mauMuiTen": "#F5C542", "dayMuiTen": 7, "giay": 10.55}} />
      <Composition id="ai-lopxe-cau4" component={AiLopxeCau4G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau4Schema} calculateMetadata={meta}
        defaultProps={{"anhBanDo": "nhan_y/70b1253d8c81f6.jpg", "anhThungLung": "nhan_y/4b372ce5c5d205.jpg", "anhCoTienCanh": "nhan_y/bf3794abd3db2d.png", "anhDanBo": "nhan_y/28611cf136787d.jpg", "chuNam": "1880", "coChuNam": 170, "mauMuc": "#b03a2a", "doRongCo": 2800, "tocDoCo": 800, "quangPanBo": 110, "phongBo": 1.08, "giay": 10.72}} />
      <Composition id="ai-lopxe-cau40" component={AiLopxeCau40G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau40Schema} calculateMetadata={meta}
        defaultProps={{"anhKySu": "nhan_y/be91f126bc512a.png", "anhMach": "nhan_y/41ecfbfe17957f.jpg", "rongKySu": 780, "diChuyenKySu": -150, "doPhong": 0.38, "zoomNhe": 0.06, "toiNen": 0.3, "mauNeon": "#35D8FF", "mauDiemSang": "#7CF0FF", "giay": 4.43}} />
      <Composition id="ai-lopxe-cau41" component={AiLopxeCau41G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau41Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/d9b9eed5d4e606.jpg", "anh_ket_cau": "nhan_y/e8108784fafd6e.png", "anh_can": "nhan_y/9ec6d22d01f0ac.jpg", "mau_luc": "#ffd166", "toi_nen": 0.35, "toi_can": 0.3, "rong_cat": 700, "cao_cat": 363, "giay": 10.79}} />
      <Composition id="ai-lopxe-cau42" component={AiLopxeCau42G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau42Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/687c4e2a3d52d7.jpg", "anh_nguoi": "nhan_y/75ba573a3da525.png", "anh_dat": "nhan_y/80ffd5596b62f7.jpg", "anh_lop": "nhan_y/2644d4b17a0327.png", "chu_dau": "KHÔNG", "quang_pan": 150, "do_zoom_nen": 1.12, "do_toi_nen": 0.12, "co_dau": 150, "mau_dau": "#c0392b", "mau_noi": "#f5c518", "rong_khung": 760, "cao_khung": 760, "do_toi_khung_phai": 0.42, "giay": 10.13}} />
      <Composition id="ai-lopxe-cau43" component={AiLopxeCau43G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau43Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/1426e13abc70ee.jpg", "anhLop": "nhan_y/4e47d125b10d75.png", "chuDiaDanh": "Quận Pima", "soLop": 1500, "donViLop": "chiếc lốp", "giayDem": 4, "coChuDiaDanh": 128, "coSoDem": 124, "rongLop": 860, "doToiNen": 0.26, "zoomDau": 1.22, "zoomCuoi": 1.02, "giay": 5.53}} />
      <Composition id="ai-lopxe-cau44" component={AiLopxeCau44G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau44Schema} calculateMetadata={meta}
        defaultProps={{"anh": "nhan_y/b93e85b40a4afc.jpg", "nam": "1996", "namX": 110, "namY": 760, "coNam": 150, "mauNam": "#F6F2E8", "zoomDau": 1, "zoomCuoi": 1.08, "toiNen": 0.12, "insetX": 1240, "insetY": 200, "insetSize": 560, "insetZoom": 4.2, "diemX": 0.44, "diemY": 0.6, "netDay": 3, "mauNet": "#F6F2E8", "giay": 9.43}} />
      <Composition id="ai-lopxe-cau45" component={AiLopxeCau45G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau45Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/aa801cd9a155c1.jpg", "anhLich": "nhan_y/6ace18147b57e9.png", "anhChiHuy": "nhan_y/4e47d125b10d75.png", "anhTinhNguyen": "nhan_y/75ba573a3da525.png", "anhCongIch": "nhan_y/2644d4b17a0327.png", "anhLenhToa": "nhan_y/eae8ecb31a6804.png", "phongNen": 1.12, "toiNen": 0.18, "gocNen": "52% 45%", "rongLich": 413, "caoLich": 616, "rongChiHuy": 644, "caoChiHuy": 448, "rongTinhNguyen": 453, "caoTinhNguyen": 595, "rongCongIch": 670, "caoLenhToa": 524, "rongLenhToa": 420, "pushCuoi": 1.055, "bienDoTroi": 4, "giay": 10.85}} />
      <Composition id="ai-lopxe-cau46" component={AiLopxeCau46G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau46Schema} calculateMetadata={meta}
        defaultProps={{"anhSaMac": "nhan_y/928f6dcd5a0d65.jpg", "anhXeng": "nhan_y/6a29a0c7d7bd5d.jpg", "anhDat": "nhan_y/b17f3e19428639.jpg", "chuDoSau": "1,2 m", "coChuDoSau": 150, "zoomSaMac": 1.1, "zoomXeng": 1.16, "zoomDat": 1.09, "doRongQuet": 460, "gocQuet": 14, "doMoQuet": 0.45, "chuKyQuet": 52, "giay": 11.8}} />
      <Composition id="ai-lopxe-cau48" component={AiLopxeCau48G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau48Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/01b7ee531a2502.jpg", "anh_coc": "nhan_y/2098aa39a4daa9.png", "bg_tu": 1.06, "bg_den": 1.16, "bg_goc": "50% 60%", "coc_w": 900, "coc_h": 600, "coc_roi_tu": 700, "beat_coc": 79, "beat_do": 85, "thu_x": 1470, "thu_tren": 400, "thu_duoi": 960, "so_do": "0.5m", "co_so": 110, "mau": "#FFD200", "giay": 5.53}} />
      <Composition id="ai-lopxe-cau49" component={AiLopxeCau49G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau49Schema} calculateMetadata={meta}
        defaultProps={{"anhMatCat": "nhan_y/9028b4a6b7312c.jpg", "anhCumLop": "nhan_y/3c611316471ff8.jpg", "anhDaiKhoa": "nhan_y/e56482664bf1a5.png", "anhCotThep": "nhan_y/45c9a23414b0f7.png", "coSo": "2,5 cm", "mau": "#FFD24A", "doPhong": 1.04, "doPhongRa": 1.16, "doPhongCum": 1.15, "doPhongCumRa": 1.0, "giay": 13.19}} />
      <Composition id="ai-lopxe-cau5" component={AiLopxeCau5G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau5Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/fbd547d13ab517.jpg", "anh_bui_co": "nhan_y/cecbbdf704612a.png", "anh_dan_bo": "nhan_y/ff5cebd7b300a2.png", "tieu_de_co": "CỎ SACATON CAO QUÁ ĐẦU BÒ", "nhan_dan_bo": "ĐÀN BÒ BỊ CHE KHUẤT", "tieu_de_suoi": "DÒNG SUỐI NÔNG UỐN LƯỢN", "nhan_suoi": "Suối nông đáy sỏi", "giay": 4.11}} />
      <Composition id="ai-lopxe-cau50" component={AiLopxeCau50G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau50Schema} calculateMetadata={meta}
        defaultProps={{"anhBoKe": "nhan_y/63411afbe4aba7.jpg", "anhBanVe": "nhan_y/f0746a87f652f1.jpg", "anhSoDo": "nhan_y/992c299dba60eb.jpg", "anhThuocDo": "nhan_y/53041e3e70c8cb.png", "doSau": 3, "donVi": "m", "coSo": 150, "coThuoc": 760, "xThuoc": 1240, "yThuoc": 170, "xSo": 940, "ySo": 460, "xVong": 340, "yVong": 300, "wVong": 620, "hVong": 430, "giay": 10.83}} />
      <Composition id="ai-lopxe-cau51" component={AiLopxeCau51G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau51Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/8353baebd31ba2.jpg", "anh_xe": "nhan_y/7f38e5bc3d0fb3.png", "chu": "14 m", "mau": "#F5C518", "co_chu": 96, "do_day": 6, "rong_xe": 700, "do_day_nen": 0.28, "giay": 10.99}} />
      <Composition id="ai-lopxe-cau52" component={AiLopxeCau52G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau52Schema} calculateMetadata={meta}
        defaultProps={{"anhXuong": "nhan_y/55b715cd108b1d.jpg", "anhGoodyear": "nhan_y/cb8d0583e78ed8.jpg", "anhPhelps": "nhan_y/05c4f2f0e1dcb6.jpg", "anhLop": "nhan_y/c6421825b722d0.png", "anhGoong": "nhan_y/0bfe7b0bc3b8ad.png", "soTien": 5000, "donVi": "$", "giayDem": 1.9, "chuThe1": "5.000 $", "chuGoodyear": "Goodyear", "chuPhelps": "Phelps Dodge", "coSo": 210, "coThe": 104, "coNhan": 96, "mauNen": "rgba(12,12,14,0.82)", "mauChu": "#FFF6D8", "mauNhan": "#F2C230", "quangXuong": 140, "toiXuong": 0.22, "toiGoodyear": 0.3, "toiPhelps": 0.28, "giay": 7.65}} />
      <Composition id="ai-lopxe-cau53" component={AiLopxeCau53G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau53Schema} calculateMetadata={meta}
        defaultProps={{"anh_giao_su": "nhan_y/bc6279cdf63d8a.jpg", "anh_dam": "nhan_y/4ca098eb66d3a6.png", "anh_tuong": "nhan_y/8890aadb81ef04.jpg", "ten_giao_su": "Stewart Hoenig", "so_tien": 35000, "don_vi_tien": "USD", "giay_dem": 1.8, "co_so": 150, "co_ten": 68, "rong_dam": 1720, "lech_whip": 1600, "zoom_nen_tu": 1.02, "zoom_nen_den": 1.18, "toi_nen": 0.12, "toi_tuong": 0.08, "giay": 13.7}} />
      <Composition id="ai-lopxe-cau54" component={AiLopxeCau54G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau54Schema} calculateMetadata={meta}
        defaultProps={{"nenBanLamViec": "nhan_y/77e64c07462f19.jpg", "tachTayTinhToan": "nhan_y/8476c7b580f010.png", "nenDapBeTong": "nhan_y/2b199e1996c0cf.jpg", "nenHemNui": "nhan_y/9a4d98f0b29276.jpg", "canDapLopXe": "nhan_y/d3e5ace4b7a464.jpg", "giay": 13.08}} />
      <Composition id="ai-lopxe-cau55" component={AiLopxeCau55G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau55Schema} calculateMetadata={meta}
        defaultProps={{"anhTuong": "nhan_y/b16883454547ec.jpg", "anhCongTruong": "nhan_y/63aaa6b9cbf690.jpg", "gocTuong": "50% 50%", "gocCongTruong": "50% 50%", "zoomTuongTu": 1, "zoomTuongDen": 1.15, "zoomCongTruongTu": 1, "zoomCongTruongDen": 1.12, "toiTuong": 0.28, "toiCongTruong": 0.22, "muiTenDx": 60, "muiTenDy": 40, "muiTenCong": 90, "mauSoDo": "#9fd0ff", "soPhanTram": 40, "donVi": "%", "giayDem": 1.2, "coSoDem": 150, "nhanThang": "THÁNG 6", "coNhanThang": 44, "mauNhan": "#ffd166", "giay": 11.38}} />
      <Composition id="ai-lopxe-cau56" component={AiLopxeCau56G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau56Schema} calculateMetadata={meta}
        defaultProps={{"nenTuongPath": "nhan_y/e3e94dfb9cce2b.jpg", "nenNuocSietPath": "nhan_y/7c9b6d1aed2a6b.jpg", "canThamQuaPath": "nhan_y/07b8f2f4432888.jpg", "tieuDe": "HÃM DÒNG CHẢY", "tocDDBanDau": 12.5, "tocDDSau": 2.1, "giay": 5.33}} />
      <Composition id="ai-lopxe-cau57" component={AiLopxeCau57G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau57Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen_site": "nhan_y/602e5e5350965e.jpg", "anh_tach_minyard": "nhan_y/8bff49300a57bd.png", "anh_can_tires": "nhan_y/bf4d96423451b3.jpg", "anh_nen_storm": "nhan_y/7ca6aa4d9553b6.jpg", "chu_ten": "MINYARD", "so_tuan": 1, "co_dong_ho": 200, "mau_nhan": "#ffcc22", "giay": 13.48}} />
      <Composition id="ai-lopxe-cau59" component={AiLopxeCau59G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau59Schema} calculateMetadata={meta}
        defaultProps={{"anhTaiLieu": "nhan_y/2e46e20b64c755.jpg", "anhThungLung": "nhan_y/724eb5a9d8ba07.jpg", "anhThanDap": "nhan_y/f89272db7fc9f1.png", "anhBao": "nhan_y/20ee98cae782e7.jpg", "anhLu": "nhan_y/d447cf564bb1c4.png", "conDau": "11/1996", "coConDau": 112, "mauConDau": "#b3261e", "rongThanDap": 900, "rongDongLu": 1150, "mauMuiTen": "#ffd23f", "doDam": 0.32, "giay": 13.2}} />
      <Composition id="ai-lopxe-cau6" component={AiLopxeCau6G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau6Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/15b17979726073.jpg", "anhBotBien": "nhan_y/0b30be9f03ce09.png", "anhDatKho": "nhan_y/c8479a8ac94a02.jpg", "zoomNenTu": 1.16, "zoomNenDen": 1.26, "panNen": 120, "botBienRong": 940, "botBienCao": 567, "botBienX": 175, "botBienY": 245, "botBienTreo": 1150, "botBienTocDo": 45, "quetSangRong": 380, "quetSangDo": 0.7, "quetSangNghieng": 16, "wipeTreo": 90, "punchDo": 0.12, "giay": 10.98}} />
      <Composition id="ai-lopxe-cau61" component={AiLopxeCau61G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau61Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/7f0d06959b3432.jpg", "anhBui": "nhan_y/1cb445f10e09d0.png", "anhMua": "nhan_y/55c8d175904b79.png", "anhLu": "nhan_y/ad3c2772ae70df.png", "doDamNen": 0.46, "doDamBui": 0.85, "doDamMua": 0.72, "doDamLu": 1, "rungBienDo": 5, "phongNen": 1.26, "giay": 11.83}} />
      <Composition id="ai-lopxe-cau62" component={AiLopxeCau62G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau62Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen_suoi": "nhan_y/cdc86009514243.jpg", "anh_song_bun": "nhan_y/55c8d175904b79.png", "anh_canh_cay": "nhan_y/808cb0c262e859.png", "anh_cat_phu_sa": "nhan_y/a1f1b796360c8c.png", "anh_dap_lop": "nhan_y/61fa10b8a43a45.jpg", "anh_john_king": "nhan_y/4f50c067230c99.jpg", "anh_ranh_xoi": "nhan_y/ed24a1f57effd9.jpg", "ten_nhan_vat": "John King", "co_ten": 92, "phong_nen1_tu": 1.02, "phong_nen1_den": 1.16, "phong_dap_tu": 1.0, "phong_dap_den": 1.18, "phong_king_tu": 1.14, "phong_king_den": 1.0, "quang_lia": 120, "phong_xoi": 1.18, "do_mo_cat": 0.6, "do_toi": 0.12, "giay": 12.52}} />
      <Composition id="ai-lopxe-cau63" component={AiLopxeCau63G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau63Schema} calculateMetadata={meta}
        defaultProps={{"nenSuoiNui": "nhan_y/6fce4ddc2b1952.jpg", "tachBunDo": "nhan_y/414e50332ee083.png", "canDapLopXe": "nhan_y/818dde32603e2d.jpg", "nenThungLungArizona": "nhan_y/75f73ad04759a9.jpg", "textChinh": "Đập Lốp Xe Đang Thi Công Bị Đe Dọa", "textLichSu": "1972 • THƯỜNG XUYÊN XẢY RA LŨ QUÉT", "labelViTri": "Thung lũng Arizona", "giay": 11.9}} />
      <Composition id="ai-lopxe-cau64" component={AiLopxeCau64G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau64Schema} calculateMetadata={meta}
        defaultProps={{"anhSuoi": "nhan_y/84cf333c072e55.jpg", "anhNhom": "nhan_y/f8856ac8547907.png", "anhDap": "nhan_y/cf337b4d4eb3cd.jpg", "anhCongTruong": "nhan_y/f50b2eea2baf85.jpg", "mauVong": "#e02020", "rongNhom": 880, "mauQuetSang": "#fff6d8", "doMoQuetSang": 0.55, "gocXoayQuet": 14, "giay": 10.49}} />
      <Composition id="ai-lopxe-cau65" component={AiLopxeCau65G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau65Schema} calculateMetadata={meta}
        defaultProps={{"anhSuoi": "nhan_y/c470aec3860f68.jpg", "anhNguoi": "nhan_y/f8856ac8547907.png", "anhLopXe": "nhan_y/a60543c04ddf08.jpg", "anhCat": "nhan_y/16e925b5ddc2ef.jpg", "quangPan": 90, "phongSuoi": 1.06, "toiSuoi": 0.12, "lechCat": 1200, "xNguoi": 320, "yNguoi": 140, "rongNguoi": 1280, "caoNguoi": 846, "zoomDau": 1.0, "zoomGiua": 1.06, "zoomCuoi": 0.86, "punchDau": 1.0, "punchCuoi": 1.34, "banKinhCat": 2000, "quetRong": 900, "giay": 12.98}} />
      <Composition id="ai-lopxe-cau67" component={AiLopxeCau67G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau67Schema} calculateMetadata={meta}
        defaultProps={{"anh_cat": "nhan_y/3fb46503d6633e.jpg", "anh_lop_xe": "nhan_y/43bbe3461519b8.png", "anh_ha_luu": "nhan_y/6f7ff6998458e8.jpg", "so_lop": 5, "quang_nen": 110, "toi_nen": 0.1, "lech_lop_xe": 640, "phong_lop_xe": 1.05, "cao_thuoc": 890, "mau_thuoc": "#FFD400", "chu_thuoc": "1 m", "co_chu_thuoc": 72, "co_so": 210, "mau_so": "#FFFFFF", "thoi_gian_xoa": 26, "toi_ha_luu": 0.1, "giay": 13.22}} />
      <Composition id="ai-lopxe-cau68" component={AiLopxeCau68G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau68Schema} calculateMetadata={meta}
        defaultProps={{"bg_lop_xe": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?q=80&w=1920&auto=format&fit=crop", "tach_lop_chan": "https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=700&auto=format&fit=crop", "can_lop_cat": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?q=80&w=1920&auto=format&fit=crop", "tach_chong_lop": "https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=500&auto=format&fit=crop", "nhan_phu_sa": "LỚP PHÙ SA ĐỌNG LẠI", "nhan_chieu_cao": "CHIỀU CAO ~ 1 MÉT", "giay": 11.12}} />
      <Composition id="ai-lopxe-cau69" component={AiLopxeCau69G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau69Schema} calculateMetadata={meta}
        defaultProps={{"anh_office": "nhan_y/09d1ab0bbf98ac.jpg", "anh_officials": "nhan_y/8266c2f5dd09e3.png", "anh_can_dam": "nhan_y/997e1a6568fe09.jpg", "anh_dam": "nhan_y/49c651cf88ba5c.jpg", "anh_beaver": "nhan_y/3ff001e39fcf92.png", "anh_nature": "nhan_y/b7900bac967826.jpg", "tu_office": 1.02, "den_office": 1.12, "tu_dam": 1.18, "den_dam": 1.04, "do_punch": 0.12, "do_quang": 96, "do_sang": 0.55, "do_nhoa": 0.5, "toi_nen": 0.12, "caoquan": 560, "caohai": 860, "giay": 13.9}} />
      <Composition id="ai-lopxe-cau7" component={AiLopxeCau7G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau7Schema} calculateMetadata={meta}
        defaultProps={{"nenKhoCan": "nhan_y/06f57debd56752.jpg", "tachReCayKho": "nhan_y/226f6fc387a583.png", "keyText": "Đất khô cằn", "giay": 3}} />
      <Composition id="ai-lopxe-cau70" component={AiLopxeCau70G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau70Schema} calculateMetadata={meta}
        defaultProps={{"anhPhuSa": "nhan_y/88e5ac5f606b8a.jpg", "anhDongChay": "nhan_y/db60bc70bca2d5.jpg", "anhHienTruong": "nhan_y/7bb9f7594e00b7.jpg", "anhQuanChuc": "nhan_y/dd20283267ef36.png", "nhanPhuSa": "PHÙ SA MÀU MỠ", "nhanThanhCong": "GIỮ ĐẤT THÀNH CÔNG", "giay": 10.74}} />
      <Composition id="ai-lopxe-cau71" component={AiLopxeCau71G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau71Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/e7fdc5e1c10b79.jpg", "anh_giao_su": "nhan_y/515e2ee7652c54.png", "anh_dat_am": "nhan_y/ece21c2598d30d.jpg", "chu_moc": "3 NĂM SAU", "co_chu_moc": 112, "mau_chu_moc": "#FFFFFF", "mau_gach": "#F2C230", "rong_gach": 560, "zoom_nen_tu": 1.02, "zoom_nen_den": 1.2, "toi_nen": 0.12, "lech_troi_giao_su": 70, "zoom_dat_tu": 1.22, "zoom_dat_den": 1.04, "toi_dat": 0.06, "giay": 7.89}} />
      <Composition id="ai-lopxe-cau72" component={AiLopxeCau72G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau72Schema} calculateMetadata={meta}
        defaultProps={{"anhKho": "nhan_y/67e9c2afd3fb97.jpg", "anhXanh": "nhan_y/632259a5fe4b63.jpg", "anhSoDo": "nhan_y/bf0bc1e487a6ea.jpg", "chuDienTich": "2 ha", "mauVien": "#F5E6B8", "coChuDienTich": 64, "daiWipe": 34, "rongSoDo": 800, "caoSoDo": 450, "giay": 12.3}} />
      <Composition id="ai-lopxe-cau73" component={AiLopxeCau73G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau73Schema} calculateMetadata={meta}
        defaultProps={{"anhNen1": "nhan_y/d5dfc0723bd906.jpg", "anhNen2": "nhan_y/358bc13939e8e5.png", "anhNen3": "nhan_y/ddad4986a6ec7f.jpg", "tieuDe": "3 năm sau", "giay": 7.27}} />
      <Composition id="ai-lopxe-cau74" component={AiLopxeCau74G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau74Schema} calculateMetadata={meta}
        defaultProps={{"anhTuongLop": "nhan_y/ee61656b80744b.jpg", "anhMatCat": "nhan_y/06e06c0dae8d10.jpg", "anhThungLung": "nhan_y/834c9d3d5b4ced.jpg", "tenDiaDanh": "Bear Creek", "coDiaDanh": 66, "nhanDx": -520, "nhanDy": 250, "doDamAnh1": 0.18, "doDamAnh2": 0.22, "doDamAnh3": 0.12, "phongNhip1": 0.05, "zoomNhip1Tu": 1.02, "zoomNhip1Den": 1.14, "zoomNhip2Tu": 1.15, "zoomNhip2Den": 1.02, "zoomNhip3Tu": 1.14, "zoomNhip3Den": 1.02, "giay": 9.73}} />
      <Composition id="ai-lopxe-cau75" component={AiLopxeCau75G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau75Schema} calculateMetadata={meta}
        defaultProps={{"anhSuoi": "nhan_y/e88cf42ba177ac.jpg", "anhCoDai": "nhan_y/6447a901f02c90.jpg", "anhDongCo": "nhan_y/3a637fa59fd9a6.jpg", "anhDanBo": "nhan_y/7a7e1aa4771784.jpg", "frameChuyen": 84, "daiNenSuoi": 102, "daiCoDai": 100, "zoomSuoiDau": 1, "zoomSuoiCuoi": 1.08, "zoomDongCoDau": 1.12, "zoomDongCoCuoi": 1, "coNang": 210, "boNang": 190, "toiNen": 0.06, "nhipCo": 55, "nhipBo": 65, "daiChuyen": 16, "giay": 9.41}} />
      <Composition id="ai-lopxe-cau76" component={AiLopxeCau76G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau76Schema} calculateMetadata={meta}
        defaultProps={{"anhNenRung": "nhan_y/953fdbbd5547a8.jpg", "anhNenVuong": "nhan_y/fef094b58efb88.jpg", "anhHuou": "nhan_y/d700e514e54438.png", "anhChoSon": "nhan_y/769c45d52cdac9.png", "anhPeccary": "nhan_y/8bba2d9b17a633.png", "bgZoomTu": 1, "bgZoomDen": 1.1, "nuocZoomTu": 1.14, "nuocZoomDen": 1, "huouRong": 780, "huouCao": 500, "huouX0": 110, "huouX1": 700, "huouY": 505, "choRong": 620, "choCao": 533, "choX": 220, "choY": 430, "pecRong": 760, "pecCao": 481, "pecX": 1120, "pecY": 520, "frameTruot": 92, "daiTruot": 12, "giay": 9.25}} />
      <Composition id="ai-lopxe-cau77" component={AiLopxeCau77G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau77Schema} calculateMetadata={meta}
        defaultProps={{"anhDatKho": "nhan_y/9c5347677c58e2.jpg", "anhThaoNguyen": "nhan_y/70380e12ca68c6.jpg", "anhTho": "nhan_y/d700e514e54438.png", "anhLinhMieu": "nhan_y/8b6b189e0ca237.png", "phongDatCuoi": 1.14, "phongThaoDau": 1.06, "phongThaoCuoi": 1.18, "daiSangRong": 520, "daiSangCao": 1700, "daiSangOpacity": 0.85, "heSoTruotPhai": 130, "lechParallaxTho": 120, "lechParallaxMieu": 70, "moTho": 5, "thoTrai": 1040, "thoTop": 520, "thoRong": 660, "mieuTrai": 300, "mieuTop": 300, "mieuRong": 540, "giay": 9.15}} />
      <Composition id="ai-lopxe-cau78" component={AiLopxeCau78G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau78Schema} calculateMetadata={meta}
        defaultProps={{"anhMatCat": "nhan_y/589c0958ff3f61.jpg", "anhRe": "nhan_y/53b8ec0220929d.png", "anhNuocNham": "nhan_y/d6a5b1dc6b3267.jpg", "zoomNenTu": 1.12, "zoomNenDen": 1.24, "toiNen": 0.06, "reRong": 1400, "zoomNuocTu": 1.03, "zoomNuocDen": 1.16, "sangOp": 0.45, "giay": 5.71}} />
      <Composition id="ai-lopxe-cau79" component={AiLopxeCau79G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau79Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/1791227bd9b846.jpg", "anhMach": "nhan_y/93d397bcdf85eb.png", "anhDat": "nhan_y/c59d3fcc449a1f.jpg", "zoomNenTu": 1, "zoomNenDen": 1.14, "toiNen": 0.1, "machRong": 960, "machCao": 479, "machTrai": 80, "machTren": 300, "theTrai": 980, "theTren": 250, "theRong": 840, "theCao": 560, "mauVien": "#f2e6c8", "mauQuet": "rgba(255,244,214,0.55)", "doDaiQuet": 52, "giay": 11.53}} />
      <Composition id="ai-lopxe-cau8" component={AiLopxeCau8G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau8Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/4c6bd8528a0efc.jpg", "anh_nguoi": "nhan_y/0d56b2b3c2c4e9.png", "anh_xoi": "nhan_y/b27c11c234027d.jpg", "anh_can": "nhan_y/4219abec6bb76c.jpg", "anh_cuoi": "nhan_y/aab3a59293b401.jpg", "quang_nen": 120, "nguoi_cao": 700, "so_km": 90, "giay_dem": 2.2, "co_dem": 150, "nhan_dem": "GẦN 90 KM", "mau_do_dac": "#F2C14E", "quang_cuoi": 90, "giay": 11.05}} />
      <Composition id="ai-lopxe-cau80" component={AiLopxeCau80G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau80Schema} calculateMetadata={meta}
        defaultProps={{"anh_dat": "nhan_y/6a232593c58958.jpg", "anh_long_dat": "nhan_y/f50fa09084ad58.jpg", "anh_nuoi_duong": "nhan_y/5968461796549f.jpg", "zoom_dat_tu": 1, "zoom_dat_den": 1.3, "zoom_long_dat_tu": 1.15, "zoom_long_dat_den": 1, "zoom_macro_tu": 1.05, "zoom_macro_den": 1.3, "dai_wipe_dat": 42, "dai_wipe_macro": 38, "mau_vach": "#ffd27a", "do_toi_dat": 0.25, "do_toi_long_dat": 0.2, "giay": 10.93}} />
      <Composition id="ai-lopxe-cau81" component={AiLopxeCau81G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau81Schema} calculateMetadata={meta}
        defaultProps={{"anhDiaHinh": "nhan_y/00d359fff1c97e.jpg", "anhCanDat": "nhan_y/da42910cbd8c44.jpg", "anhGioCat": "nhan_y/ea5c0d4ef8720b.jpg", "toiNen": 0.12, "zoomDiaHinhTu": 1, "zoomDiaHinhDen": 1.1, "zoomDatAmTu": 1.16, "zoomDatAmDen": 1, "zoomGioCatTu": 1.18, "zoomGioCatDen": 1, "nhip2": 83, "nhip3": 173, "doTruot": 24, "coVongNhip1": 560, "coVongNhip2": 520, "coVongNhip3": 640, "giay": 9.61}} />
      <Composition id="ai-lopxe-cau82" component={AiLopxeCau82G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau82Schema} calculateMetadata={meta}
        defaultProps={{"anhBeTong": "nhan_y/10f025c91f4f92.jpg", "anhRung": "nhan_y/a047f21accfc76.jpg", "anhThucVat": "nhan_y/e8ae8b3788c7a5.jpg", "mauNhan": "#E8B23A", "muiTenDx": 130, "muiTenDy": -45, "muiTenCong": 70, "vongW": 560, "vongH": 340, "kinhSize": 620, "netBanDo": 6, "giay": 9.01}} />
      <Composition id="ai-lopxe-cau83" component={AiLopxeCau83G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau83Schema} calculateMetadata={meta}
        defaultProps={{"anhBanDo": "nhan_y/ae2895c2949ce4.jpg", "anhThamHiem": "nhan_y/799944b411cc95.png", "anhSong": "nhan_y/c565049f9bcd84.jpg", "anhHaiLyCanCanh": "nhan_y/fe9a6d592f816c.jpg", "anhHaiLyBoi": "nhan_y/7651c97f74a35b.png", "anhHaiLyBay": "nhan_y/a5af1c548008cb.png", "nam": 1825, "tenNhaThamHiem": "James Ohio Pattie", "mauDuong": "#c0392b", "mauChu": "#3a2410", "coNam": 240, "coTen": 56, "doDayNet": 9, "giay": 10.67}} />
      <Composition id="ai-lopxe-cau84" component={AiLopxeCau84G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau84Schema} calculateMetadata={meta}
        defaultProps={{"anhDap": "nhan_y/16a518bea14361.jpg", "anhNuoc": "nhan_y/046180383acb7b.jpg", "anhNgap": "nhan_y/5430688c3ba1f7.jpg", "beat1": 10, "beat2": 143, "beat3": 247, "zoomDau": 1, "zoomCuoi": 1.14, "quangLia": 70, "doToi": 0.32, "doWipe": 30, "doTruot": 26, "doAmAnh": 0.5, "giay": 12.12}} />
      <Composition id="ai-lopxe-cau85" component={AiLopxeCau85G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau85Schema} calculateMetadata={meta}
        defaultProps={{"mapImage": "nhan_y/7fe683044d6c3a.jpg", "explorerImage": "nhan_y/1812ca277935ae.jpg", "riverImage": "nhan_y/a557c6cfef8169.jpg", "beaverCutout": "nhan_y/ddcab0e63bad93.png", "manyBeaversImage": "nhan_y/eb3713f79b50e6.jpg", "mainTitle": "San Pedro: Xưa là vương quốc hải ly", "yearText": "1825", "giay": 10.01}} />
      <Composition id="ai-lopxe-cau86" component={AiLopxeCau86G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau86Schema} calculateMetadata={meta}
        defaultProps={{"anh1": "nhan_y/115612352eee83.jpg", "anh2": "nhan_y/5729c04a01ebf3.jpg", "anh3": "nhan_y/1063a2b95a56c6.jpg", "chuNhan": "Lông hải ly", "coNhan": 68, "mauKinh": "#b08d3f", "toi1": 0.35, "toi2": 0.4, "toi3": 0.42, "giay": 7.95}} />
      <Composition id="ai-lopxe-cau87" component={AiLopxeCau87G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau87Schema} calculateMetadata={meta}
        defaultProps={{"anh_rung": "nhan_y/1b8b54821c8a21.jpg", "anh_tho_san": "nhan_y/b6b85673e9e39a.png", "anh_suoi": "nhan_y/adeaaafc8d8ccb.jpg", "anh_bay_trong": "nhan_y/81cc8ea1eaf1f8.jpg", "chu_moc": "Đầu thế kỷ XX", "co_chu_moc": 132, "zoom_rung_tu": 1.02, "zoom_rung_den": 1.14, "zoom_suoi": 1.12, "quang_suoi": 90, "rong_tho_san": 1000, "x_tho_san": 560, "y_tho_san": 430, "mau_wipe": "rgba(255,244,214,0.55)", "do_sepia": 0.85, "do_toi": 0.62, "co_flash": 0.55, "giay": 7.53}} />
      <Composition id="ai-lopxe-cau88" component={AiLopxeCau88G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau88Schema} calculateMetadata={meta}
        defaultProps={{"anhNen": "nhan_y/465318abb0a2a6.jpg", "anhNuoc": "nhan_y/cb81f8e8a35e10.jpg", "anhDat": "nhan_y/67c4aacd44be89.jpg", "anhRanh": "nhan_y/9d0b367184a11d.jpg", "f1": 0, "f2": 130, "f3": 280, "f4": 430, "dai1": 160, "dai2": 180, "dai3": 180, "dai4": 170, "zoomNenTu": 1, "zoomNenDen": 1.12, "zoomNuocTu": 1.15, "zoomNuocDen": 1, "zoomDatTu": 1.05, "zoomDatDen": 1.15, "zoomRanhTu": 1, "zoomRanhDen": 1.08, "daiTruot": 26, "punchDau": 1.14, "punchCuoi": 1.04, "toiNen": 0.42, "toiNuoc": 0.38, "toiDat": 0.4, "toiRanh": 0.36, "toiVien": 0.62, "giay": 10.27}} />
      <Composition id="ai-lopxe-cau89" component={AiLopxeCau89G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau89Schema} calculateMetadata={meta}
        defaultProps={{"anh_map": "nhan_y/781d82daaf50b9.jpg", "anh_o_phan_tich": "nhan_y/27c9d94a5417fd.jpg", "anh_ngap_nuoc": "nhan_y/0f610ee9b2e50c.jpg", "anh_long_suoi": "nhan_y/cb311e8b654b10.jpg", "map_zoom_tu": 1.1, "map_zoom_den": 1.02, "map_goc": "46% 42%", "map_toi": 0.1, "o_zoom_tu": 1.06, "o_zoom_den": 1.0, "o_moc_hien": 24, "o_moc_tan": 128, "diem1_x": 430, "diem1_y": 470, "diem2_x": 1450, "diem2_y": 402, "diem3_x": 872, "diem3_y": 828, "moc_do_1": 18, "moc_do_2": 49, "moc_do_3": 95, "nuoc_zoom_tu": 1.06, "nuoc_zoom_den": 1.16, "nuoc_toi": 0.08, "mau_vang": "#c8a24a", "bieu_do_x": 1260, "bieu_do_y": 700, "bieu_do_w": 560, "bieu_do_h": 230, "bieu_do_moc": 20, "suoi_zoom_tu": 1.0, "suoi_zoom_den": 1.16, "suoi_toi": 0.06, "giay": 10.29}} />
      <Composition id="ai-lopxe-cau9" component={AiLopxeCau9G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau9Schema} calculateMetadata={meta}
        defaultProps={{"anhDongCo": "nhan_y/f08edb360a7eed.jpg", "anhTrangTrai": "nhan_y/c1f9eab3e8d601.jpg", "anhDanBo": "nhan_y/c09386dd07c8e6.jpg", "chuQuyetDinh": "Đất khô cằn", "coChuQuyetDinh": 64, "chuNam": "1870", "coChuNam": 96, "soBo": 40, "donViBo": "con bò", "giayDem": 4, "coSoDem": 76, "mauChu": "#f2e6d0", "giay": 11.08}} />
      <Composition id="ai-lopxe-cau90" component={AiLopxeCau90G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau90Schema} calculateMetadata={meta}
        defaultProps={{"anh_lich_su": "nhan_y/b567b92a797311.jpg", "anh_may_moc": "nhan_y/87c429ceefe440.jpg", "anh_vung_dat": "nhan_y/8e2e676cce24ff.jpg", "moc_thoi_gian": "1 THẾ KỶ", "so_tien": 1, "don_vi_tien": "TRIỆU ĐÔ LA", "giay_dem": 1.8, "co_moc": 150, "co_dem": 116, "mau_chu": "#F6E9CE", "giay": 9.51}} />
      <Composition id="ai-lopxe-cau91" component={AiLopxeCau91G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau91Schema} calculateMetadata={meta}
        defaultProps={{"anhBanDo": "nhan_y/86c4407d4d7286.jpg", "anhInset": "nhan_y/cc863cc162c31d.png", "anhHoSo": "nhan_y/91339de4d81bfe.jpg", "mauGhim": "#c8321f", "mauMoc": "#b3221c", "chuMoc": "ĐÃ HỦY", "phongToCuoi": 1.36, "gocPhong": "50% 52%", "toiBanDo": 0.12, "giay": 9.87}} />
      <Composition id="ai-lopxe-cau92" component={AiLopxeCau92G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau92Schema} calculateMetadata={meta}
        defaultProps={{"anhHonig": "nhan_y/d7a5553eac3de3.jpg", "anhSoDo": "nhan_y/e43a31d8114429.png", "anhBanGiay": "nhan_y/9452aba6dce88e.jpg", "zoomHonigTu": 1.08, "zoomHonigDen": 1.18, "panPhai": 45, "zoomBanTu": 1.2, "zoomBanDen": 1.0, "zoomThemTu": 1.05, "zoomThemDen": 1.0, "toiHonig": 0.16, "toiBan": 0.18, "doSangDau": 0.9, "rongSoDo": 700, "caoSoDo": 410, "demSoDo": 20, "mauKhung": "#f7f2e6", "mauVien": "#e6d9b8", "mauGach": "rgba(200,58,44,0.88)", "dayGach": 15, "giay": 6.49}} />
      <Composition id="ai-lopxe-cau93" component={AiLopxeCau93G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau93Schema} calculateMetadata={meta}
        defaultProps={{"anh_nen": "nhan_y/0510814a7d8beb.jpg", "anh_cong_nhan": "nhan_y/f1dc49c7727375.png", "so_luong": 1500, "co_so": 170, "mau_so": "#FFFFFF", "vi_tri_so_x": 128, "vi_tri_so_y": 140, "do_toi_nen": 0.1, "do_toi_cuoi": 0.85, "le_vao": 170, "phong_nen": 1.08, "do_phong_cong_nhan": 1.34, "giay": 12.53}} />
      <Composition id="ai-lopxe-cau94" component={AiLopxeCau94G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau94Schema} calculateMetadata={meta}
        defaultProps={{"anhLaoDong": "nhan_y/fca3fa1605bde4.jpg", "anhMuiTen": "nhan_y/7269ca59d2fe37.png", "anhXuong": "nhan_y/8a48decbc6aa7c.jpg", "anhMayEp": "nhan_y/b9882495eb8c8a.jpg", "anhCongTruong": "nhan_y/45ddbb0c9ea589.jpg", "anhKhoiCaoSu": "nhan_y/386087f4550ab7.png", "anhLapDat": "nhan_y/afc38cc0569e1e.jpg", "anhCanCau": "nhan_y/750765546b2be6.png", "chuTan": "1 TẤN", "mauNhan": "#FFD400", "coNhan": 108, "rongKhoi": 720, "caoKhoi": 448, "xKhoi": 560, "yKhoi": 470, "xNhan": 1178, "yNhan": 398, "nangLen": 230, "xCanCau": 940, "yCanCau": -60, "rongCanCau": 980, "caoCanCau": 654, "xMuiTen": 1010, "yMuiTen": 150, "rongMuiTen": 800, "caoMuiTen": 500, "giay": 12.96}} />
      <Composition id="ai-lopxe-cau95" component={AiLopxeCau95G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau95Schema} calculateMetadata={meta}
        defaultProps={{"tieuDe": "NHÂN CÔNG KHỔNG LỒ", "nhanSoLuong": "1,500 LỐP XE", "soToiDa": 1500, "anhNen": "nhan_y/26c8e12905e767.jpg", "anhLop": "nhan_y/24b2be19111728.png", "anhDayThep": "nhan_y/b6b3b1254fef54.png", "anhXengSoi": "nhan_y/e210d4ee742633.png", "giay": 11.87}} />
      <Composition id="ai-lopxe-cau96" component={AiLopxeCau96G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau96Schema} calculateMetadata={meta}
        defaultProps={{"anhNenSuoi": "nhan_y/98f6dcddd15fc8.jpg", "anhGiaoSu": "nhan_y/2fa5233418d1d7.png", "anhCanLop": "nhan_y/da9600b4b64371.jpg", "anhBeTong": "nhan_y/1f3f99f46f9ef3.jpg", "punchScale": 1.12, "sweepOpacity": 0.55, "sweepAngle": 14, "toiNen": 0.12, "concreteZoom": 1.08, "giaoSuZoom": 1.05, "giaoSuMo": 0.95, "vienRong": 8, "vienMau": "rgba(238,232,214,0.85)", "boGoc": 6, "giay": 12.57}} />
      <Composition id="ai-lopxe-cau97" component={AiLopxeCau97G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau97Schema} calculateMetadata={meta}
        defaultProps={{"anhNuoc": "nhan_y/5c8be7eb892413.jpg", "anhFort": "nhan_y/93274bc0f0c0ec.jpg", "nhanDiaDanh": "Fort Lauderdale, Florida - 1972", "coNhan": 90, "mauNhan": "#FFFFFF", "mauApLuc": "#FFC61A", "doToiNen1": 0.32, "doToiNen2": 0.22, "doDayThanh": 10, "doDayMuiTen": 12, "doDayDuongNoi": 4, "giay": 13.18}} />
      <Composition id="ai-lopxe-cau98" component={AiLopxeCau98G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau98Schema} calculateMetadata={meta}
        defaultProps={{"anhSuoiLop": "nhan_y/f2644e057d7620.jpg", "anhBaiRac": "nhan_y/7d30bd55751e05.jpg", "anhBeTong": "nhan_y/ad48222b977475.jpg", "textThamMy": "Thẩm mỹ dòng suối", "textGiaiPhap": "Giải pháp bê tông", "giay": 11.97}} />
      <Composition id="ai-lopxe-cau99" component={AiLopxeCau99G} width={1920} height={1080} fps={FPS} durationInFrames={150} schema={AiLopxeCau99Schema} calculateMetadata={meta}
        defaultProps={{"anhFlorida": "nhan_y/e9b0c8c94709b6.jpg", "anhTroiBien": "nhan_y/3f253421e0e715.jpg", "anhBien": "nhan_y/e70ba79582f880.jpg", "anhLopDo": "nhan_y/c185ab59ce1695.jpg", "anhKhinhKhiCau": "nhan_y/1c9c1eaecf23fb.png", "anhSaLan": "nhan_y/a006277ff222ab.png", "nhanNgay": "01.04.1972", "coNhanNgay": 34, "mauNhanNgay": "#f5e6c8", "coKhinhKhiCau": 380, "coSaLan": 980, "doToiNen": 0.18, "doToiCanh": 0.22, "giay": 12.35}} />
      {/* NHAN_Y_SUA_KET_THUC */}
    </Folder>
  </>
);
