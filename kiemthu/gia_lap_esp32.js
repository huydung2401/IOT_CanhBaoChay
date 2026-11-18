#!/usr/bin/env node
/*
 * Giả lập 2 ESP32 (esp01: 101-110, esp02: 111-120) gửi tin MQTT đúng mẫu JSON mục 4.2 + 10.2 (v1.2).
 * Dùng khi làm Task 2/3 mà chưa có Wokwi, hoặc để demo nhanh dashboard.
 *
 * Cài:   npm install mqtt
 * Chạy:  node gia_lap_esp32.js                    (broker.emqx.io)
 *        node gia_lap_esp32.js mqtt://localhost:1883
 *
 * Lệnh gõ khi đang chạy (giống lệnh Serial của ESP32, mục 7.3, cộng thêm vài lệnh):
 *   dat <phong> <nhiet_do>   ép nhiệt độ           tha <phong>     bỏ ép
 *   loi <phong>              giả lập cảm biến hỏng  hetloi <phong>  hết hỏng
 *   khoi <phong>             có khói (MQ-2)         hetkhoi <phong> hết khói
 *   tattieng <esp01|esp02>   bấm nút tắt tiếng 5 phút
 *   capdien <phong|all>      giữ nút 3 s: cấp lại điện phòng đã hết báo động
 *   dung <esp01|esp02>       ngừng gửi (mô phỏng rớt mạng / dừng Wokwi)
 *   chay <esp01|esp02>       gửi lại
 *   reset <esp01|esp02>      khởi động lại thiết bị (seq về 0, mất trạng thái)
 *   trangthai                in bảng phòng      thoat
 */
const mqtt = require('mqtt');

// Phải trùng với TIEN_TO_TOPIC trong canhbaochay_mqtt.h và Node-RED
const TIEN_TO_TOPIC = 'canhbaochay_HUIT73915/nhatro01';
const NGUONG_BAT_C = 45, NGUONG_TAT_C = 40, NGUONG_CHU_Y_C = 38, NGUONG_HET_CHU_Y_C = 36, SO_LAN_XAC_NHAN = 2;
const THOI_GIAN_TAT_TIENG_MS = 300000;
const CHU_KY_DOC_MS = 2000, CHU_KY_GUI_MS = 5000;

class ThietBi {
  constructor(ma, dsPhong, client) {
    this.ma = ma; this.dsPhong = dsPhong; this.client = client;
    this.dangChay = true;
    this.khoiTao();
    this.tDoc = setInterval(() => this.doc(), CHU_KY_DOC_MS);
    this.tGui = setInterval(() => this.guiTatCa(), CHU_KY_GUI_MS);
  }
  khoiTao() {
    this.phong = {};
    this.tatTiengDen = 0; this.mucLucTatTieng = {};
    for (const p of this.dsPhong) {
      const nhiet = 28 + Math.random() * 3;
      this.phong[p] = { nhiet, giaTri: nhiet, ep: null, loi: false, baoDong: false,
                        loiCamBien: false, dem: 0, seq: 0, daGui: null,
                        demChuY: 0, chuY: false, khoi: false, ngatDien: false };
    }
  }
  doc() {
    for (const [ma, r] of Object.entries(this.phong)) {
      if (r.ep === null) r.nhiet = Math.min(32, Math.max(27, r.nhiet + (Math.random() - 0.5) * 0.4));
      const t = r.loi ? null : (r.ep !== null ? r.ep : r.nhiet);
      if (t === null) { r.loiCamBien = true; r.dem = 0; continue; }   // TB-05: giữ baoDong
      r.loiCamBien = false;
      r.dem = t >= NGUONG_BAT_C ? r.dem + 1 : 0;
      if (!r.baoDong && r.dem >= SO_LAN_XAC_NHAN) r.baoDong = true;
      else if (r.baoDong && t <= NGUONG_TAT_C) r.baoDong = false;
      r.demChuY = t >= NGUONG_CHU_Y_C ? r.demChuY + 1 : 0;              // MR-02
      if (!r.chuY && r.demChuY >= SO_LAN_XAC_NHAN) r.chuY = true;
      else if (r.chuY && t <= NGUONG_HET_CHU_Y_C) r.chuY = false;
      r.giaTri = t;
    }
    this.kiemThayDoi();
  }
  muc(r) {                                                            // MR-02
    if (r.khoi && (r.chuY || r.baoDong)) return 3;
    if (r.baoDong || r.khoi) return 2;
    return r.chuY ? 1 : 0;
  }
  tatTieng() {                                                        // MR-05
    if (!this.tatTiengDen) return false;
    if (Date.now() >= this.tatTiengDen) { this.tatTiengDen = 0; return false; }
    for (const [ma, r] of Object.entries(this.phong))
      if (this.muc(r) > (this.mucLucTatTieng[ma] || 0)) { this.tatTiengDen = 0; return false; }
    return true;
  }
  dauHieu(r) { return `${this.muc(r)}|${r.loiCamBien}|${r.khoi}|${r.ngatDien}|${this.tatTieng()}`; }
  kiemThayDoi() {
    for (const [ma, r] of Object.entries(this.phong)) {
      if (r.baoDong || this.muc(r) === 3) r.ngatDien = true;          // MR-04: chốt
      if (r.daGui !== this.dauHieu(r)) this.gui(ma);                  // TT-04
    }
  }
  gui(ma) {
    if (!this.dangChay || !this.client.connected) return;
    const r = this.phong[ma];
    const json = {
      ma_thiet_bi: this.ma, ma_phong: ma,
      nhiet_do: r.loiCamBien || r.giaTri === undefined ? null : Math.round(r.giaTri * 10) / 10,
      bao_dong: this.muc(r) >= 2, loi_cam_bien: r.loiCamBien, seq: r.seq,
      muc: this.muc(r), khoi: r.khoi, ngat_dien: r.ngatDien, tat_tieng: this.tatTieng(),
      ts: Math.floor(Date.now() / 1000)
    };
    this.client.publish(`${TIEN_TO_TOPIC}/phong/${ma}/dulieu`, JSON.stringify(json));
    r.seq++;
    r.daGui = this.dauHieu(r);
  }
  guiTatCa() { for (const ma of this.dsPhong) this.gui(ma); }
  dung() { clearInterval(this.tDoc); clearInterval(this.tGui); }
}

function batDau(url, inLog = true) {
  const client = mqtt.connect(url, { clientId: 'canhbaochay_gialap_' + Math.random().toString(16).slice(2, 8) });
  const ds = [
    new ThietBi('esp01', Array.from({ length: 10 }, (_, i) => String(101 + i)), client),
    new ThietBi('esp02', Array.from({ length: 10 }, (_, i) => String(111 + i)), client),
  ];
  client.on('connect', () => { if (inLog) console.log('[mqtt] da ket noi', url); ds.forEach(d => d.guiTatCa()); });
  client.on('error', e => console.error('[mqtt] loi', e.message));

  const timPhong = ma => { for (const d of ds) if (d.phong[ma]) return d.phong[ma]; return null; };
  const timTb = ma => ds.find(d => d.ma === ma);
  const timTbCuaPhong = ma => ds.find(d => d.phong[ma]);

  function lenh(dong) {
    const [l, a, b] = dong.trim().split(/\s+/);
    if (!l) return;
    const r = a ? timPhong(a) : null, tb = a ? timTb(a) : null;
    switch (l) {
      case 'dat': if (r) r.ep = parseFloat(b); break;
      case 'tha': if (r) r.ep = null; break;
      case 'loi': if (r) r.loi = true; break;
      case 'hetloi': if (r) r.loi = false; break;
      case 'khoi': if (r) { r.khoi = true; timTbCuaPhong(a).kiemThayDoi(); } break;
      case 'hetkhoi': if (r) { r.khoi = false; timTbCuaPhong(a).kiemThayDoi(); } break;
      case 'tattieng':
        if (tb) { tb.mucLucTatTieng = {}; for (const [m, x] of Object.entries(tb.phong)) tb.mucLucTatTieng[m] = tb.muc(x);
                  tb.tatTiengDen = Date.now() + THOI_GIAN_TAT_TIENG_MS; tb.kiemThayDoi(); }
        break;
      case 'capdien':
        for (const d of ds) for (const [m, x] of Object.entries(d.phong))
          if ((a === 'all' || a === m) && x.ngatDien && d.muc(x) < 2) x.ngatDien = false;
        ds.forEach(d => d.kiemThayDoi());
        break;
      case 'dung': if (tb) tb.dangChay = false; break;
      case 'chay': if (tb) { tb.dangChay = true; tb.guiTatCa(); } break;
      case 'reset': if (tb) { tb.khoiTao(); tb.guiTatCa(); } break;
      case 'trangthai':
        for (const d of ds) for (const [ma, x] of Object.entries(d.phong))
          console.log(d.ma, ma, x.loiCamBien ? 'null' : (x.giaTri ?? x.nhiet).toFixed(1),
                      'muc ' + d.muc(x), x.loiCamBien ? 'LOI' : '-', x.khoi ? 'KHOI' : '-',
                      x.ngatDien ? 'NGAT DIEN' : '-', d.dangChay ? '' : '(dung)');
        return;
      case 'thoat': ds.forEach(d => d.dung()); client.end(); process.exit(0);
      default: console.log('Lenh: dat, tha, loi, hetloi, khoi, hetkhoi, tattieng, capdien, dung, chay, reset, trangthai, thoat'); return;
    }
    if (inLog) console.log('OK:', dong.trim());
  }
  return { client, ds, lenh };
}

if (require.main === module) {
  const { lenh } = batDau(process.argv[2] || 'mqtt://broker.emqx.io:1883');
  require('readline').createInterface({ input: process.stdin }).on('line', lenh);
}
module.exports = { batDau, ThietBi };
