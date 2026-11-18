#!/usr/bin/env python3
"""
Sinh các file flow Node-RED của CanhBaoChay (SRS v1.2, mục 3.3, 3.4, 4.4, 7.4, 10).

  luong_bangdieukhien.json  - tab BangDieuKhien (Task 2): sơ đồ mặt bằng 20 phòng, 6 trạng thái
  luong_lichsu.json         - tab LichSu (Task 3): SQLite, biểu đồ, chi tiết phòng, Telegram 2 chiều
  luong_tong_hop.json       - cả hai tab, dùng để import một lần khi đã ghép

Cần cài trong Node-RED (Manage palette): @flowfuse/node-red-dashboard, node-red-node-sqlite.
Chạy lại script sau khi sửa code trong file này:  python3 nodered/tao_flow.py
"""
import json, pathlib

GOC = pathlib.Path(__file__).resolve().parent

# ĐỔI dãy số 73915 cho trùng với TIEN_TO_TOPIC trong canhbaochay_mqtt.h
TIEN_TO_TOPIC = "canhbaochay_HUIT73915/nhatro01"
BROKER = "broker.emqx.io"

# DB-07: danh sách phòng cố định (mã thiết bị -> phòng)
DANH_SACH = {
    "esp01": [str(n) for n in range(101, 111)],
    "esp02": [str(n) for n in range(111, 121)],
}
TAT_CA_PHONG = [p for ds in DANH_SACH.values() for p in ds]

# ---------------------------------------------------------------- cấu hình dùng chung
# Cùng id trong cả hai file: import file thứ hai thì chọn bỏ qua các node đã có.
CAU_HINH = [
    {"id": "cbc_broker", "type": "mqtt-broker", "name": "Broker CanhBaoChay", "broker": BROKER,
     "port": "1883", "clientid": "", "autoConnect": True, "usetls": False, "protocolVersion": "4",
     "keepalive": "30", "cleansession": True, "autoUnsubscribe": True,
     "birthTopic": "", "birthQos": "0", "birthRetain": "false", "birthPayload": "", "birthMsg": {},
     "closeTopic": "", "closeQos": "0", "closeRetain": "false", "closePayload": "", "closeMsg": {},
     "willTopic": "", "willQos": "0", "willRetain": "false", "willPayload": "", "willMsg": {},
     "userProps": "", "sessionExpiry": ""},
    {"id": "cbc_ui_base", "type": "ui-base", "name": "CanhBaoChay", "path": "/dashboard",
     "includeClientData": True, "acceptsClientConfig": ["ui-notification", "ui-control"],
     "showPathInSidebar": False, "navigationStyle": "default", "titleBarStyle": "default"},
    {"id": "cbc_ui_theme", "type": "ui-theme", "name": "CanhBaoChay",
     "colors": {"surface": "#263238", "primary": "#c62828", "bgPage": "#eceff1",
                "groupBg": "#ffffff", "groupOutline": "#cfd8dc"},
     "sizes": {"density": "default", "pagePadding": "12px", "groupGap": "12px",
               "groupBorderRadius": "6px", "widgetGap": "12px"}},
]

# ================================================================ TAB BANGDIEUKHIEN
FN_NAP_DANH_SACH = r"""
// DB-07: danh sách 20 phòng cố định. Phòng chưa từng gửi tin sẽ hiện
// MẤT KẾT NỐI sau 15 s kể từ lúc Node-RED khởi động (DB-03, K17).
const DANH_SACH = %s;
const now = Date.now();
const cu = flow.get('phong') || {};
const phong = {};
for (const [thietBi, dsPhong] of Object.entries(DANH_SACH)) {
    for (const ma of dsPhong) {
        phong[ma] = (cu[ma] && cu[ma].coTin) ? cu[ma] : {
            ma_phong: ma, ma_thiet_bi: thietBi, coTin: false, lanCuoi: now,
            nhiet_do: null, bao_dong: false, loi_cam_bien: false, tinMat: 0,
            muc: 0, khoi: false, ngat_dien: false, tat_tieng: false, ts: null
        };
    }
}
flow.set('phong', phong);
node.status({ fill: 'blue', shape: 'dot', text: Object.keys(phong).length + ' phòng' });
return null;
""" % json.dumps(DANH_SACH)

FN_CAP_NHAT_PHONG = r"""
// Ghi tin MQTT vào đúng phòng (mục 4.2), theo dõi seq (DB-09)
const p = msg.payload;
if (!p || typeof p !== 'object' || typeof p.ma_phong !== 'string') {
    node.warn('Tin sai mẫu JSON trên ' + msg.topic + ': ' + JSON.stringify(p));
    return null;
}
const phong = flow.get('phong');
if (!phong) return null;                       // chưa nạp danh sách
const r = phong[p.ma_phong];
if (!r) {
    node.warn('Phòng ngoài danh sách DB-07: ' + p.ma_phong);
    return null;
}
const now = Date.now();
if (typeof p.seq === 'number') {
    if (typeof r.seq === 'number') {
        if (p.seq < r.seq) r.khoiDongLai = now;                       // seq lùi (về 0): ESP32 reset
        else if (p.seq > r.seq + 1) r.tinMat = (r.tinMat || 0) + (p.seq - r.seq - 1);
    }
    r.seq = p.seq;
}
r.coTin = true;
r.ma_thiet_bi = p.ma_thiet_bi || r.ma_thiet_bi;
r.nhiet_do = (typeof p.nhiet_do === 'number') ? p.nhiet_do : null;
r.bao_dong = p.bao_dong === true;
r.loi_cam_bien = p.loi_cam_bien === true;
// v1.2 (mục 10.2): thiết bị cũ không gửi "muc" thì suy ra từ bao_dong
r.muc = (typeof p.muc === 'number') ? p.muc : (r.bao_dong ? 2 : 0);
r.khoi = p.khoi === true;
r.ngat_dien = p.ngat_dien === true;
r.tat_tieng = p.tat_tieng === true;
r.ts = (typeof p.ts === 'number' && p.ts > 0) ? p.ts : null;
r.lanCuoi = now;
flow.set('phong', phong);
return null;
"""

FN_TINH_TRANG_THAI = r"""
// Quy tắc hiển thị mục 4.4 + 10.4, xét theo thứ tự, dừng ở điều kiện đúng đầu tiên:
// MẤT KẾT NỐI > NGUY HIỂM > BÁO ĐỘNG > LỖI CẢM BIẾN > CHÚ Ý > BÌNH THƯỜNG
const THOI_GIAN_MAT_KET_NOI_S = 15;
const phong = flow.get('phong');
if (!phong) return null;
const now = Date.now();
const truoc = context.get('matKhiBaoDong') || {};
const ds = [];
const tong = { nguyHiem: 0, baoDong: 0, loi: 0, chuY: 0, matKetNoi: 0, binhThuong: 0 };
const telegram = [];

for (const ma of Object.keys(phong).sort()) {
    const r = phong[ma];
    const mat = now - r.lanCuoi > THOI_GIAN_MAT_KET_NOI_S * 1000;
    const loi = r.coTin && (r.loi_cam_bien || r.nhiet_do === null);
    const muc = r.muc || 0;
    let trangThai, vienDo = false, ghiChu = '';
    if (mat) {                                                   // 1. MẤT KẾT NỐI
        trangThai = 'MẤT KẾT NỐI'; tong.matKetNoi++;
        if (!r.coTin) ghiChu = 'chưa nhận tin nào';
        else if (r.bao_dong) { vienDo = true; ghiChu = 'mất kết nối khi đang báo động'; }  // DB-08
    } else if (muc >= 3) {                                       // 2. NGUY HIỂM
        trangThai = 'NGUY HIỂM'; tong.nguyHiem++; ghiChu = 'khói + nhiệt cao';
    } else if (muc >= 2 || r.bao_dong) {                         // 3. BÁO ĐỘNG
        trangThai = 'BÁO ĐỘNG'; tong.baoDong++;
        ghiChu = r.khoi ? 'phát hiện khói' : 'nhiệt độ cao';
        if (loi) { vienDo = true; ghiChu += ', kèm lỗi cảm biến'; }
    } else if (loi) {                                            // 4. LỖI CẢM BIẾN
        trangThai = 'LỖI CẢM BIẾN'; tong.loi++;
    } else if (muc === 1) {                                      // 5. CHÚ Ý
        trangThai = 'CHÚ Ý'; tong.chuY++; ghiChu = 'nhiệt độ ≥ 38 °C';
    } else {                                                     // 6. BÌNH THƯỜNG
        trangThai = 'BÌNH THƯỜNG'; tong.binhThuong++;
    }

    // DB-10: báo Telegram một lần khi phòng rơi vào "mất kết nối khi đang báo động"
    const mkbd = mat && r.coTin && r.bao_dong;
    if (mkbd && !truoc[ma]) telegram.push({ payload: { ma_phong: ma, loai: 'mat_ket_noi_khi_bao_dong', luc: now } });
    truoc[ma] = mkbd;

    ds.push({
        ma, ma_thiet_bi: r.ma_thiet_bi, trangThai, vienDo, ghiChu, muc,
        nhietDo: r.nhiet_do, cu: mat, loi: !!loi,
        khoi: !!r.khoi, ngatDien: !!r.ngat_dien, tatTieng: !!r.tat_tieng,
        capNhat: r.coTin ? r.lanCuoi : null, seq: (typeof r.seq === 'number') ? r.seq : null,
        ts: r.ts || null, lechGio: r.ts ? Math.round(now / 1000 - r.ts) : null,
        khoiDongLai: (r.khoiDongLai && now - r.khoiDongLai < 10 * 60 * 1000) ? r.khoiDongLai : null,
        tinMat: r.tinMat || 0
    });
}
context.set('matKhiBaoDong', truoc);

// MR-16: nhật ký trạng thái. So với lần tính trước, mỗi thay đổi ghi một dòng vào bảng nhat_ky.
const nk = [];
const cu = context.get('nhatKyTruoc') || {};
const NK_SQL = 'INSERT INTO nhat_ky (thoi_gian, ma_phong, ma_thiet_bi, loai, tu, den, nhiet_do, ghi_chu) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)';
const ghiNk = (ma, tb, loai, tu, den, t, ghi) => nk.push({ topic: NK_SQL, payload: [now, ma, tb, loai, tu, den, t, ghi || null], muc: 'nk_ghi' });
const tatTiengTb = {}, khoiDongTb = {};
for (const p of ds) {
    const r = phong[p.ma];
    if (!r.coTin) continue;                              // chưa từng có tin: chưa có gì để ghi
    const t = (typeof p.nhietDo === 'number') ? p.nhietDo : null;
    const c = cu[p.ma];
    if (!c) {                                            // lần đầu thấy phòng (Node-RED vừa chạy)
        if (p.trangThai !== 'BÌNH THƯỜNG') ghiNk(p.ma, p.ma_thiet_bi, 'trang_thai', 'Node-RED khởi động', p.trangThai, t, p.ghiChu);
    } else {
        if (c.tt !== p.trangThai) ghiNk(p.ma, p.ma_thiet_bi, 'trang_thai', c.tt, p.trangThai, t, p.ghiChu);
        if (!p.cu && c.nd !== p.ngatDien) ghiNk(p.ma, p.ma_thiet_bi, 'dien', c.nd ? 'ngắt' : 'có điện', p.ngatDien ? 'ngắt' : 'có điện', t,
                                               p.ngatDien ? 'rơ-le ngắt điện phòng' : 'đã cấp lại điện (giữ nút 3 s)');
        if (!p.cu && c.tat !== p.tatTieng) tatTiengTb[p.ma_thiet_bi] = p.tatTieng;
        if (p.khoiDongLai && p.khoiDongLai !== c.kdl) khoiDongTb[p.ma_thiet_bi] = true;
    }
    cu[p.ma] = { tt: p.trangThai, nd: c && p.cu ? c.nd : p.ngatDien, tat: c && p.cu ? c.tat : p.tatTieng, kdl: p.khoiDongLai };
}
for (const [tb, bat] of Object.entries(tatTiengTb))  // tắt tiếng là của cả thiết bị (một tầng): ghi một dòng
    ghiNk(null, tb, 'tat_tieng', bat ? 'còi bật' : 'tắt tiếng', bat ? 'tắt tiếng' : 'còi bật', null,
          bat ? 'bấm nút tắt tiếng (5 phút)' : 'hết tắt tiếng');
for (const tb of Object.keys(khoiDongTb)) ghiNk(null, tb, 'khoi_dong_lai', null, null, null, 'thiết bị khởi động lại (seq về 0)');
context.set('nhatKyTruoc', cu);

const kq = { phong: ds, tongHop: tong, luc: now };
global.set('trangThaiPhong', kq);       // cho trang Chi tiết phòng và lệnh Telegram /trangthai
return [{ payload: kq }, telegram.length ? telegram : null, nk.length ? nk : null];
"""

FN_MO_CHI_TIET = r"""
// MR-11: bấm vào một phòng trên sơ đồ -> chuyển sang trang "Chi tiết phòng" của đúng trình duyệt đó
if (msg.muc !== 'chi_tiet' || typeof msg.payload !== 'string') return null;
global.set('phongChiTiet', msg.payload);
return [{ payload: { page: 'Chi tiết phòng' }, _client: msg._client },
        { payload: msg.payload, muc: 'chi_tiet' }];
"""

TPL_SO_DO = r"""<template>
  <div class="cbc" v-if="msg && msg.payload">
    <div class="tong-hop">
      <span class="chip nh" v-if="t.nguyHiem">Nguy hiểm: {{ t.nguyHiem }}</span>
      <span class="chip bd">Báo động: {{ t.baoDong }}</span>
      <span class="chip cy">Chú ý: {{ t.chuY }}</span>
      <span class="chip loi">Lỗi cảm biến: {{ t.loi }}</span>
      <span class="chip mat">Mất kết nối: {{ t.matKetNoi }}</span>
      <span class="chip bt">Bình thường: {{ t.binhThuong }}</span>
      <span class="luc">Cập nhật {{ gio(msg.payload.luc) }} · bấm vào phòng để xem chi tiết</span>
    </div>
    <div v-for="tang in cacTang" :key="tang.ten" class="tang">
      <div class="ten-tang">{{ tang.ten }}</div>
      <div class="mat-bang">
        <div class="loi-ra trai"><span class="bieu">🚪</span><b>LỐI THOÁT</b><span>🪜 Cầu thang A</span></div>
        <div v-for="p in tang.tren" :key="p.ma" :class="oPhong(p)" @click="mo(p)" :title="'Phòng ' + p.ma + ': ' + p.trangThai">
          <div class="dau"><b>{{ p.ma }}</b><span class="icon">{{ bieuTuong(p) }}</span></div>
          <div :class="['nhiet', { cu: p.cu }]">{{ nhiet(p) }}</div>
          <div class="tt">{{ p.trangThai }}</div>
        </div>
        <div class="loi-ra phai"><span class="bieu">🚪</span><b>LỐI THOÁT</b><span>🪜 Cầu thang B</span></div>
        <div class="hanh-lang">
          <span>🧯</span><span class="chu-hl">HÀNH LANG · {{ tang.coiChung }}</span><span>🧯</span>
        </div>
        <div v-for="p in tang.duoi" :key="p.ma" :class="oPhong(p)" @click="mo(p)" :title="'Phòng ' + p.ma + ': ' + p.trangThai">
          <div class="dau"><b>{{ p.ma }}</b><span class="icon">{{ bieuTuong(p) }}</span></div>
          <div :class="['nhiet', { cu: p.cu }]">{{ nhiet(p) }}</div>
          <div class="tt">{{ p.trangThai }}</div>
        </div>
      </div>
    </div>
    <div class="chu-giai">
      <span><i class="m bt"></i>Bình thường</span><span><i class="m cy"></i>Chú ý ≥ 38 °C</span>
      <span><i class="m bd"></i>Báo động</span><span><i class="m nh"></i>Nguy hiểm</span>
      <span><i class="m loi"></i>Lỗi cảm biến</span><span><i class="m mat"></i>Mất kết nối</span>
      <span>💨 khói · 🔌 đã ngắt điện · 🔕 đang tắt tiếng · ⚠️ lỗi cảm biến</span>
    </div>
  </div>
  <div v-else class="cho">Đang chờ dữ liệu...</div>
</template>

<script>
export default {
  computed: {
    t() { return this.msg.payload.tongHop; },
    cacTang() {
      const ds = this.msg.payload.phong;
      const tang = [];
      for (let k = 0; k * 10 < ds.length; k++) {
        const phong = ds.slice(k * 10, k * 10 + 10);
        const mucMax = Math.max(0, ...phong.filter(p => !p.cu).map(p => p.muc || 0));
        const tatTieng = phong.some(p => p.tatTieng && !p.cu);
        tang.push({
          ten: 'Tầng ' + (k + 1) + ' (' + (phong[0] ? phong[0].ma_thiet_bi : '') + ')',
          tren: phong.slice(0, 5), duoi: phong.slice(5, 10),
          coiChung: tatTieng ? 'còi chung đang tắt tiếng' : (mucMax >= 3 ? 'còi chung KÊU LIÊN TỤC' : mucMax === 2 ? 'còi chung đang kêu' : 'còi chung im')
        });
      }
      return tang;
    }
  },
  methods: {
    lop(t) {
      return { 'BÌNH THƯỜNG': 'bt', 'CHÚ Ý': 'cy', 'BÁO ĐỘNG': 'bd', 'NGUY HIỂM': 'nh',
               'LỖI CẢM BIẾN': 'loi', 'MẤT KẾT NỐI': 'mat' }[t] || '';
    },
    oPhong(p) { return ['phong', this.lop(p.trangThai), { 'vien-do': p.vienDo }]; },
    bieuTuong(p) {
      return (p.khoi ? '💨' : '') + (p.ngatDien ? '🔌' : '') + (p.tatTieng ? '🔕' : '') + (p.loi && p.trangThai !== 'LỖI CẢM BIẾN' ? '⚠️' : '');
    },
    nhiet(p) { return p.nhietDo === null ? '--' : p.nhietDo.toFixed(1) + '°'; },
    gio(ms) { return new Date(ms).toLocaleTimeString('vi-VN', { hour12: false }); },
    mo(p) { this.send({ payload: p.ma, muc: 'chi_tiet' }); }
  }
}
</script>

<style scoped>
.cbc { width: 100%; font-family: system-ui, sans-serif; }
.tong-hop { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 10px; }
.chip { padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 14px; }
.chip.nh { background: #4a0000; color: #fff; }
.chip.bd { background: #ffebee; color: #b71c1c; }
.chip.cy { background: #fffde7; color: #8d6e00; }
.chip.loi { background: #f3e5f5; color: #6a1b9a; }
.chip.mat { background: #eceff1; color: #455a64; }
.chip.bt { background: #e8f5e9; color: #1b5e20; }
.luc { margin-left: auto; color: #607d8b; font-size: 13px; }
.tang { margin-bottom: 14px; }
.ten-tang { font-weight: 700; color: #37474f; margin-bottom: 4px; }
.mat-bang { display: grid; grid-template-columns: 70px repeat(5, minmax(0, 1fr)) 70px;
            grid-template-rows: auto 34px auto; gap: 6px; background: #cfd8dc; padding: 6px; border-radius: 8px; }
.loi-ra { grid-row: 1 / span 3; display: flex; flex-direction: column; align-items: center; justify-content: center;
          gap: 4px; background: #e8f5e9; border: 2px dashed #2e7d32; border-radius: 6px; color: #1b5e20;
          font-size: 11px; text-align: center; padding: 4px; }
.loi-ra.trai { grid-column: 1; } .loi-ra.phai { grid-column: 7; }
.loi-ra .bieu { font-size: 22px; }
.hanh-lang { grid-column: 2 / span 5; grid-row: 2; display: flex; align-items: center; justify-content: space-between;
             background: repeating-linear-gradient(90deg, #eceff1 0 18px, #e0e6e9 18px 36px); border-radius: 4px; padding: 0 10px; }
.chu-hl { color: #546e7a; font-size: 12px; font-weight: 600; letter-spacing: .5px; }
.phong { border: 2px solid transparent; border-radius: 6px; padding: 6px 8px; min-height: 78px; cursor: pointer;
         transition: transform .1s; user-select: none; }
.phong:hover { transform: scale(1.03); box-shadow: 0 2px 6px rgba(0,0,0,.25); }
.phong.bt { background: #e8f5e9; border-color: #a5d6a7; }
.phong.cy { background: #fff59d; border-color: #f9a825; }
.phong.bd { background: #ffcdd2; border-color: #c62828; animation: nhay 1s infinite; }
.phong.nh { background: #7f0000; border-color: #ff1744; color: #fff; animation: nhay3 .4s infinite; }
.phong.loi { background: #e1bee7; border-color: #8e24aa; }
.phong.mat { background: #eceff1; border-color: #90a4ae; }
.phong.vien-do { border: 4px solid #c62828; }
@keyframes nhay { 50% { background: #ef9a9a; } }
@keyframes nhay3 { 50% { background: #d50000; } }
.dau { display: flex; justify-content: space-between; font-size: 13px; }
.icon { font-size: 13px; }
.nhiet { font-size: 22px; font-weight: 700; }
.nhiet.cu { color: #90a4ae; }
.tt { font-weight: 700; font-size: 12px; }
.bt .tt { color: #1b5e20; } .cy .tt { color: #8d6e00; } .bd .tt { color: #b71c1c; }
.loi .tt { color: #6a1b9a; } .mat .tt { color: #455a64; } .nh .tt { color: #fff; }
.chu-giai { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #455a64; align-items: center; }
.m { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 4px; vertical-align: -2px; }
.m.bt { background: #a5d6a7; } .m.cy { background: #fdd835; } .m.bd { background: #e57373; }
.m.nh { background: #7f0000; } .m.loi { background: #ba68c8; } .m.mat { background: #b0bec5; }
.cho { color: #607d8b; }
@media (max-width: 760px) {
  .mat-bang { grid-template-columns: 44px repeat(5, minmax(0, 1fr)) 44px; }
  .loi-ra b, .loi-ra span:not(.bieu) { display: none; }
  .nhiet { font-size: 16px; }
}
</style>
"""

TAB_BDK = "cbc_tab_bdk"
BANG_DIEU_KHIEN = [
    {"id": TAB_BDK, "type": "tab", "label": "BangDieuKhien", "disabled": False,
     "info": "Task 2 - SRS CanhBaoChay v1.2 mục 3.3, 4.4, 10.\nSơ đồ mặt bằng 20 phòng, 6 trạng thái, bấm phòng mở trang chi tiết."},
    {"id": "cbc_page_bdk", "type": "ui-page", "name": "Bảng điều khiển", "ui": "cbc_ui_base",
     "path": "/bangdieukhien", "icon": "home", "layout": "grid", "theme": "cbc_ui_theme",
     "order": 1, "className": "", "visible": "true", "disabled": "false"},
    {"id": "cbc_grp_luoi", "type": "ui-group", "name": "Nhà trọ 01 - sơ đồ mặt bằng", "page": "cbc_page_bdk",
     "width": "12", "height": "1", "order": 1, "showTitle": True, "className": "",
     "visible": "true", "disabled": "false"},
    {"id": "cbc_bdk_inject_ds", "type": "inject", "z": TAB_BDK, "name": "Khởi động",
     "props": [{"p": "payload"}], "repeat": "", "crontab": "", "once": True, "onceDelay": "0.1",
     "topic": "", "payload": "", "payloadType": "date", "x": 140, "y": 80, "wires": [["cbc_bdk_fn_ds"]]},
    {"id": "cbc_bdk_fn_ds", "type": "function", "z": TAB_BDK, "name": "Nạp danh sách phòng (DB-07)",
     "func": FN_NAP_DANH_SACH, "outputs": 1, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "",
     "libs": [], "x": 380, "y": 80, "wires": [[]]},
    {"id": "cbc_bdk_mqtt_in", "type": "mqtt in", "z": TAB_BDK, "name": "Dữ liệu phòng",
     "topic": f"{TIEN_TO_TOPIC}/phong/+/dulieu", "qos": "0", "datatype": "json", "broker": "cbc_broker",
     "nl": False, "rap": True, "rh": 0, "inputs": 0, "x": 140, "y": 160, "wires": [["cbc_bdk_fn_cn"]]},
    {"id": "cbc_bdk_fn_cn", "type": "function", "z": TAB_BDK, "name": "Cập nhật phòng",
     "func": FN_CAP_NHAT_PHONG, "outputs": 1, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "",
     "libs": [], "x": 380, "y": 160, "wires": [[]]},
    {"id": "cbc_bdk_inject_1s", "type": "inject", "z": TAB_BDK, "name": "Mỗi 1 s",
     "props": [{"p": "payload"}], "repeat": "1", "crontab": "", "once": True, "onceDelay": "0.5",
     "topic": "", "payload": "", "payloadType": "date", "x": 140, "y": 240, "wires": [["cbc_bdk_fn_tt"]]},
    {"id": "cbc_bdk_fn_tt", "type": "function", "z": TAB_BDK, "name": "Tính trạng thái (mục 4.4)",
     "func": FN_TINH_TRANG_THAI, "outputs": 3, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "",
     "libs": [], "outputLabels": ["sơ đồ", "Telegram", "nhật ký"], "x": 380, "y": 240,
     "wires": [["cbc_bdk_tpl_luoi"], ["cbc_bdk_link_tg"], ["cbc_bdk_link_nk"]]},
    {"id": "cbc_bdk_link_nk", "type": "link out", "z": TAB_BDK, "name": "sang LichSu: nhật ký",
     "mode": "link", "links": ["cbc_ls_link_nk"], "x": 640, "y": 320, "wires": []},
    {"id": "cbc_bdk_tpl_luoi", "type": "ui-template", "z": TAB_BDK, "group": "cbc_grp_luoi", "page": "",
     "ui": "", "name": "Sơ đồ mặt bằng (MR-10)", "order": 1, "width": "0", "height": "0", "head": "",
     "format": TPL_SO_DO, "storeOutMessages": True, "passthru": False, "resendOnRefresh": True,
     "templateScope": "local", "className": "", "x": 650, "y": 220, "wires": [["cbc_bdk_fn_ct"]]},
    {"id": "cbc_bdk_fn_ct", "type": "function", "z": TAB_BDK, "name": "Mở chi tiết phòng (MR-11)",
     "func": FN_MO_CHI_TIET, "outputs": 2, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "",
     "libs": [], "outputLabels": ["đổi trang", "sang LichSu"], "x": 900, "y": 220,
     "wires": [["cbc_bdk_ctrl"], ["cbc_bdk_link_ct"]]},
    {"id": "cbc_bdk_ctrl", "type": "ui-control", "z": TAB_BDK, "name": "Đổi trang", "ui": "cbc_ui_base",
     "events": "all", "x": 1120, "y": 200, "wires": [[]]},
    {"id": "cbc_bdk_link_ct", "type": "link out", "z": TAB_BDK, "name": "sang LichSu: chi tiết",
     "mode": "link", "links": ["cbc_ls_link_ct"], "x": 1120, "y": 240, "wires": []},
    {"id": "cbc_bdk_link_tg", "type": "link out", "z": TAB_BDK, "name": "sang LichSu: Telegram",
     "mode": "link", "links": ["cbc_ls_link_tg"], "x": 640, "y": 280, "wires": []},
]

# ================================================================ TAB LICHSU
FN_KHOI_TAO = r"""
// Ghi chú: node sqlite chỉ gắn tham số khi số dấu $ bằng số phần tử msg.payload, nên dùng $1, $2...
// Chạy tuần tự: mỗi câu lệnh xong mới gửi câu kế tiếp (tránh SELECT trước CREATE).
// CSDL tạo từ bản v1.1 thiếu các cột v1.2: đọc PRAGMA rồi ALTER TABLE đúng cột còn thiếu.
const TAO = [
    'CREATE TABLE IF NOT EXISTS su_kien (id INTEGER PRIMARY KEY AUTOINCREMENT, ma_phong TEXT NOT NULL, bat_dau INTEGER NOT NULL, ket_thuc INTEGER, nhiet_do_max REAL, muc_max INTEGER, co_khoi INTEGER, ngat_dien INTEGER, xac_nhan_boi TEXT, xac_nhan_luc INTEGER)',
    'CREATE TABLE IF NOT EXISTS do_nhiet (ma_phong TEXT NOT NULL, thoi_gian INTEGER NOT NULL, nhiet_do REAL NOT NULL)',
    'CREATE INDEX IF NOT EXISTS ix_do_nhiet ON do_nhiet (ma_phong, thoi_gian)',
    'CREATE INDEX IF NOT EXISTS ix_su_kien ON su_kien (ma_phong, bat_dau)',
    'CREATE TABLE IF NOT EXISTS nhat_ky (id INTEGER PRIMARY KEY AUTOINCREMENT, thoi_gian INTEGER NOT NULL, ma_phong TEXT, ma_thiet_bi TEXT, loai TEXT NOT NULL, tu TEXT, den TEXT, nhiet_do REAL, ghi_chu TEXT)',
    'CREATE INDEX IF NOT EXISTS ix_nhat_ky ON nhat_ky (thoi_gian)',
    'CREATE INDEX IF NOT EXISTS ix_nhat_ky_phong ON nhat_ky (ma_phong, thoi_gian)',
    'PRAGMA table_info(su_kien)'
];
const COT_V12 = { muc_max: 'INTEGER', co_khoi: 'INTEGER', ngat_dien: 'INTEGER', xac_nhan_boi: 'TEXT', xac_nhan_luc: 'INTEGER' };
let hang;
if (msg.muc !== 'khoitao') {
    hang = TAO.slice();                                   // bắt đầu từ inject "Khởi động"
} else {
    hang = context.get('hang') || [];
    if (msg.topic === 'PRAGMA table_info(su_kien)') {
        const co = new Set((msg.payload || []).map(r => r.name));
        for (const [cot, kieu] of Object.entries(COT_V12)) {
            if (!co.has(cot)) hang.push(`ALTER TABLE su_kien ADD COLUMN ${cot} ${kieu}`);
        }
        if (hang.length) node.warn('Nâng cấp bảng su_kien lên v1.2: ' + hang.join('; '));
    }
}
if (hang.length) {
    const sql = hang.shift();
    context.set('hang', hang);
    return { topic: sql, payload: [], muc: 'khoitao' };
}
// LS-04, K12: nạp các đợt còn mở để đóng đúng sau khi Node-RED khởi động lại
return { topic: 'SELECT ma_phong, bat_dau, nhiet_do_max, muc_max, co_khoi, ngat_dien FROM su_kien WHERE ket_thuc IS NULL', payload: [], muc: 'dot_mo' };
"""

FN_NAP_DOT_MO = r"""
const dotMo = {};
for (const r of (msg.payload || [])) dotMo[r.ma_phong] = {
    batDau: r.bat_dau, tmax: r.nhiet_do_max, mucMax: r.muc_max || 2, khoi: !!r.co_khoi, ngatDien: !!r.ngat_dien };
flow.set('dotMo', dotMo);
flow.set('sanSang', true);
node.status({ fill: 'green', shape: 'dot', text: 'CSDL sẵn sàng, ' + Object.keys(dotMo).length + ' đợt đang mở' });
return [{ muc: 'xa_hang_doi' }, { topic: SQL_BANG, payload: [], muc: 'bang' }];
""".replace("SQL_BANG", json.dumps(
    "SELECT id, ma_phong, bat_dau, ket_thuc, nhiet_do_max, muc_max, co_khoi, ngat_dien, xac_nhan_boi, xac_nhan_luc FROM su_kien ORDER BY bat_dau DESC LIMIT 50"))

FN_PHAT_HIEN_DOT = r"""
// LS-02 + MR-12: phát hiện đợt báo động (bao_dong = muc >= 2). Chỉ đóng đợt khi nhận tin
// bao_dong = false; mất kết nối (không có tin) thì không làm gì, đợt vẫn mở (K18).
// Trong đợt ghi lại cấp cao nhất, có khói hay không, có ngắt điện hay không.
function xuLy(p) {
    const sql = [], tg = [];
    if (!p || typeof p.ma_phong !== 'string') return [sql, tg];
    const now = Date.now();
    const ma = p.ma_phong;
    const t = (typeof p.nhiet_do === 'number') ? p.nhiet_do : null;
    const muc = (typeof p.muc === 'number') ? p.muc : (p.bao_dong === true ? 2 : 0);
    const khoi = p.khoi === true, nd = p.ngat_dien === true;
    if (t !== null) {
        sql.push({ topic: 'INSERT INTO do_nhiet (ma_phong, thoi_gian, nhiet_do) VALUES ($1, $2, $3)', payload: [ma, now, t], muc: 'ghi_nhiet' });
    }
    const dotMo = flow.get('dotMo') || {};
    const dot = dotMo[ma];
    if (p.bao_dong === true && !dot) {
        dotMo[ma] = { batDau: now, tmax: t, mucMax: muc, khoi, ngatDien: nd };
        sql.push({ topic: 'INSERT INTO su_kien (ma_phong, bat_dau, ket_thuc, nhiet_do_max, muc_max, co_khoi, ngat_dien) VALUES ($1, $2, NULL, $3, $4, $5, $6)',
                   payload: [ma, now, t, muc, khoi ? 1 : 0, nd ? 1 : 0], muc: 'su_kien' });
        tg.push({ payload: { ma_phong: ma, loai: muc >= 3 ? 'nguy_hiem' : 'bao_dong', nhiet_do: t, muc, khoi, ngat_dien: nd, luc: now, batDau: now } });
    } else if (p.bao_dong === true && dot) {
        let doi = false;
        if (t !== null && (dot.tmax === null || t > dot.tmax)) { dot.tmax = t; doi = true; }   // bỏ qua null (lỗi cảm biến)
        if (muc > dot.mucMax) {
            if (muc >= 3) tg.push({ payload: { ma_phong: ma, loai: 'nguy_hiem', nhiet_do: t, muc, khoi, ngat_dien: nd, luc: now, batDau: dot.batDau } });
            dot.mucMax = muc; doi = true;
        }
        if (khoi && !dot.khoi) { dot.khoi = true; doi = true; }
        if (nd && !dot.ngatDien) { dot.ngatDien = true; doi = true; }
        if (doi) {
            sql.push({ topic: 'UPDATE su_kien SET nhiet_do_max = $1, muc_max = $2, co_khoi = $3, ngat_dien = $4 WHERE ma_phong = $5 AND ket_thuc IS NULL',
                       payload: [dot.tmax, dot.mucMax, dot.khoi ? 1 : 0, dot.ngatDien ? 1 : 0, ma], muc: 'su_kien' });
        }
    } else if (p.bao_dong === false && dot) {
        delete dotMo[ma];
        sql.push({ topic: 'UPDATE su_kien SET ket_thuc = $1 WHERE ma_phong = $2 AND ket_thuc IS NULL', payload: [now, ma], muc: 'su_kien' });
        tg.push({ payload: { ma_phong: ma, loai: 'het_bao_dong', nhiet_do: t, luc: now, batDau: dot.batDau, tmax: dot.tmax, mucMax: dot.mucMax, ngat_dien: nd } });
    }
    flow.set('dotMo', dotMo);
    return [sql, tg];
}

// Chưa nạp xong các đợt đang mở thì xếp hàng, tránh tạo đợt trùng
if (msg.muc === 'xa_hang_doi') {
    const hang = context.get('hangDoi') || [];
    context.set('hangDoi', []);
    const ra = [[], []];
    for (const p of hang) { const r = xuLy(p); ra[0].push(...r[0]); ra[1].push(...r[1]); }
    return ra;
}
if (!flow.get('sanSang')) {
    const hang = context.get('hangDoi') || [];
    hang.push(msg.payload);
    context.set('hangDoi', hang.slice(-500));
    return null;
}
return xuLy(msg.payload);
"""

FN_TRUY_VAN_BIEU_DO = r"""
// LS-01: lấy 30 phút gần nhất của phòng đang chọn
if (msg.muc === 'chon_phong' && typeof msg.payload === 'string') flow.set('phongChon', msg.payload);
const ma = flow.get('phongChon') || '101';
const tu = Date.now() - 30 * 60 * 1000;
return { topic: 'SELECT thoi_gian, nhiet_do FROM do_nhiet WHERE ma_phong = $1 AND thoi_gian >= $2 ORDER BY thoi_gian',
         payload: [ma, tu], muc: 'bieudo', phong: ma, tu };
"""

FN_DINH_DANG_BIEU_DO = r"""
const rows = msg.payload || [];
msg.payload = {
    phong: msg.phong, tu: msg.tu, den: Date.now(),
    diem: rows.map(r => [r.thoi_gian, r.nhiet_do]),
    nguongBat: 45, nguongTat: 40, nguongChuY: 38
};
return msg;
"""

FN_DON_DEP = r"""
// Giữ 24 giờ nhiệt độ cho biểu đồ, 90 ngày nhật ký trạng thái; bảng su_kien giữ vĩnh viễn
return [[{ topic: 'DELETE FROM do_nhiet WHERE thoi_gian < $1', payload: [Date.now() - 24 * 3600 * 1000], muc: 'don_dep' },
         { topic: 'DELETE FROM nhat_ky WHERE thoi_gian < $1', payload: [Date.now() - 90 * 24 * 3600 * 1000], muc: 'don_dep' }]];
"""

FN_TELEGRAM = r"""
// DB-10 + MR-13: đặt TELEGRAM_TOKEN, TELEGRAM_CHAT_ID (và tuỳ chọn TELEGRAM_CHAT_ID_2 để
// leo thang) trong Environment của tab LichSu (double-click tab > Environment). Trống thì không gửi.
// KHÔNG ghi token vào file flow khi nộp bài / đưa lên GitHub.
const API = env.get('TELEGRAM_API') || 'https://api.telegram.org';
const token = env.get('TELEGRAM_TOKEN');
const chatId = env.get('TELEGRAM_CHAT_ID');
if (!token || !chatId) {
    node.status({ fill: 'grey', shape: 'ring', text: 'chưa cấu hình Telegram' });
    return null;
}
const x = msg.payload || {};
const now = Date.now();
const khoa = x.ma_phong + '|' + x.loai;
const lanGui = context.get('lanGui') || {};
if (lanGui[khoa] && now - lanGui[khoa] < 60 * 1000) return null;   // tối đa 1 tin / 60 s mỗi loại
lanGui[khoa] = now;
context.set('lanGui', lanGui);

if (!x.batDau) {                                       // tin từ BangDieuKhien không có thời điểm bắt đầu đợt
    const dot = (flow.get('dotMo') || {})[x.ma_phong];
    x.batDau = dot ? dot.batDau : 0;
}
const gio = ms => new Date(ms).toLocaleTimeString('vi-VN', { hour12: false, timeZone: 'Asia/Ho_Chi_Minh' });
const nhiet = v => (typeof v === 'number') ? v.toFixed(1) + ' °C' : 'không rõ (lỗi cảm biến)';
const them = (x.khoi ? '\n💨 Cảm biến khói: CÓ KHÓI' : '') + (x.ngat_dien ? '\n🔌 Đã tự ngắt điện phòng' : '');
let text, coNut = true;
if (x.loai === 'nguy_hiem') {
    text = `🚨🔥 NGUY HIỂM phòng ${x.ma_phong} lúc ${gio(x.luc || now)}: có khói và nhiệt độ cao (${nhiet(x.nhiet_do)}).${them}\nGọi 114 nếu xác nhận có cháy!`;
} else if (x.loai === 'bao_dong') {
    text = `🔥 BÁO ĐỘNG phòng ${x.ma_phong} lúc ${gio(x.luc || now)}, nhiệt độ ${nhiet(x.nhiet_do)}.${them}`;
} else if (x.loai === 'mat_ket_noi_khi_bao_dong') {
    text = `⚠️ Phòng ${x.ma_phong} MẤT KẾT NỐI khi đang báo động (${gio(x.luc || now)}). Hãy kiểm tra trực tiếp!`;
} else if (x.loai === 'het_bao_dong') {
    const phut = x.batDau ? Math.round((now - x.batDau) / 60000) : '?';
    text = `✅ Phòng ${x.ma_phong} hết báo động lúc ${gio(x.luc || now)} (kéo dài ~${phut} phút, cao nhất ${nhiet(x.tmax)}).` +
           (x.ngat_dien ? '\n🔌 Điện phòng vẫn đang ngắt: kiểm tra xong giữ nút TẮT TIẾNG 3 s để cấp lại.' : '');
    coNut = false;
    const cho = flow.get('tgCho') || {};             // hết đợt thì thôi leo thang
    for (const k of Object.keys(cho)) if (cho[k].ma === x.ma_phong) delete cho[k];
    flow.set('tgCho', cho);
} else {
    return null;
}
msg.method = 'POST';
msg.url = `${API}/bot${token}/sendMessage`;
msg.headers = { 'Content-Type': 'application/json' };
msg.payload = { chat_id: chatId, text };
if (coNut) msg.payload.reply_markup = { inline_keyboard: [[{ text: '✅ Đã xử lý', callback_data: `xn|${x.ma_phong}|${x.batDau}` }]] };
msg.tg = { loai: 'gui', ma: x.ma_phong, batDau: x.batDau, chatId, text, coNut };
node.status({ fill: 'green', shape: 'dot', text: 'gửi ' + x.loai + ' ' + gio(now) });
return msg;
"""

FN_TG_POLL = r"""
// MR-13: hỏi Telegram có bấm nút / lệnh mới không (getUpdates, không cần IP công khai)
const API = env.get('TELEGRAM_API') || 'https://api.telegram.org';
const token = env.get('TELEGRAM_TOKEN');
if (!token || !env.get('TELEGRAM_CHAT_ID')) return null;
const dang = flow.get('tgDangHoi') || 0;
if (Date.now() - dang < 20000) return null;          // lần hỏi trước chưa trả lời
flow.set('tgDangHoi', Date.now());
const offset = flow.get('tgOffset') || 0;
const loc = encodeURIComponent(JSON.stringify(['message', 'callback_query']));
return { method: 'GET', url: `${API}/bot${token}/getUpdates?offset=${offset}&timeout=0&allowed_updates=${loc}`,
         payload: '', headers: {}, tg: { loai: 'hoi' } };
"""

FN_TG_LEO_THANG = r"""
// MR-14: sau 120 s chưa ai bấm "Đã xử lý" thì gửi cho người thứ hai (TELEGRAM_CHAT_ID_2);
// không có người thứ hai thì nhắc lại trong nhóm chính. Mỗi sự cố leo thang 1 lần.
const LEO_THANG_S = 120;
const API = env.get('TELEGRAM_API') || 'https://api.telegram.org';
const token = env.get('TELEGRAM_TOKEN');
const chat1 = env.get('TELEGRAM_CHAT_ID');
if (!token || !chat1) return null;
const chat2 = env.get('TELEGRAM_CHAT_ID_2') || '';
const cho = flow.get('tgCho') || {};
const now = Date.now();
const ra = [];
for (const [k, e] of Object.entries(cho)) {
    if (e.leoThang || now - e.luc < LEO_THANG_S * 1000) continue;
    e.leoThang = true;
    const den = chat2 || chat1;
    const text = (chat2 ? '⏫ LEO THANG: ' : '⏰ NHẮC LẠI: ') + `chưa ai xác nhận sau ${LEO_THANG_S / 60} phút!\n\n` + e.tin[0].text;
    ra.push({ method: 'POST', url: `${API}/bot${token}/sendMessage`, headers: { 'Content-Type': 'application/json' },
              payload: { chat_id: den, text, reply_markup: { inline_keyboard: [[{ text: '✅ Đã xử lý', callback_data: 'xn|' + k }]] } },
              tg: { loai: 'leo_thang', khoa: k, chatId: den, text } });
}
flow.set('tgCho', cho);
if (ra.length) node.status({ fill: 'red', shape: 'dot', text: 'leo thang ' + ra.length + ' sự cố' });
return ra.length ? [ra] : null;
"""

FN_TG_KET_QUA = r"""
// Xử lý mọi phản hồi từ Telegram API. Ra 1: thêm yêu cầu gửi Telegram; ra 2: câu lệnh SQLite.
const API = env.get('TELEGRAM_API') || 'https://api.telegram.org';
const token = env.get('TELEGRAM_TOKEN');
const DUOC_PHEP = [env.get('TELEGRAM_CHAT_ID'), env.get('TELEGRAM_CHAT_ID_2')].filter(Boolean).map(String);
const tg = msg.tg || {};
const kq = (msg.payload && typeof msg.payload === 'object') ? msg.payload : { ok: false, description: String(msg.payload) };
const gio = ms => new Date(ms).toLocaleTimeString('vi-VN', { hour12: false, timeZone: 'Asia/Ho_Chi_Minh' });
const goi = (phuongThuc, body) => ({ method: 'POST', url: `${API}/bot${token}/${phuongThuc}`,
                                     headers: { 'Content-Type': 'application/json' }, payload: body, tg: { loai: phuongThuc } });
const cho = flow.get('tgCho') || {};
const guiDi = [], sql = [];

if (tg.loai === 'hoi') flow.set('tgDangHoi', 0);
if (!kq.ok) {
    if (tg.loai !== 'answerCallbackQuery') node.warn('Telegram ' + (tg.loai || '') + ' lỗi: ' + (kq.description || msg.statusCode));
    node.status({ fill: 'red', shape: 'ring', text: 'lỗi ' + (tg.loai || '') + ' ' + gio(Date.now()) });
    return null;
}

if (tg.loai === 'gui' && tg.coNut && kq.result) {             // nhớ tin để leo thang / sửa khi xác nhận
    const k = tg.ma + '|' + tg.batDau;
    const tin = { chatId: tg.chatId, messageId: kq.result.message_id, text: tg.text };
    if (cho[k]) cho[k].tin.push(tin);
    else cho[k] = { ma: tg.ma, batDau: tg.batDau, luc: Date.now(), leoThang: false, tin: [tin] };
} else if (tg.loai === 'leo_thang' && kq.result && cho[tg.khoa]) {
    cho[tg.khoa].tin.push({ chatId: tg.chatId, messageId: kq.result.message_id, text: tg.text });
} else if (tg.loai === 'hoi') {
    let offset = flow.get('tgOffset') || 0;
    for (const u of (kq.result || [])) {
        offset = Math.max(offset, u.update_id + 1);
        const cq = u.callback_query;
        if (cq) {
            const chat = String(cq.message && cq.message.chat ? cq.message.chat.id : '');
            if (!DUOC_PHEP.includes(chat)) {
                guiDi.push(goi('answerCallbackQuery', { callback_query_id: cq.id, text: 'Bạn không có quyền xác nhận.' }));
                continue;
            }
            const [lenh, ma, batDau] = String(cq.data || '').split('|');
            if (lenh !== 'xn') continue;
            const ai = [cq.from.first_name, cq.from.last_name].filter(Boolean).join(' ') + (cq.from.username ? ' (@' + cq.from.username + ')' : '');
            const now = Date.now();
            const k = ma + '|' + batDau;
            const e = cho[k];
            if (!e) {
                guiDi.push(goi('answerCallbackQuery', { callback_query_id: cq.id, text: 'Sự cố này đã được xác nhận hoặc đã kết thúc.' }));
                guiDi.push(goi('editMessageReplyMarkup', { chat_id: cq.message.chat.id, message_id: cq.message.message_id, reply_markup: { inline_keyboard: [] } }));
                continue;
            }
            delete cho[k];
            guiDi.push(goi('answerCallbackQuery', { callback_query_id: cq.id, text: 'Đã ghi nhận. Cảm ơn!' }));
            for (const t of e.tin) {                        // sửa mọi tin của sự cố này (kể cả tin leo thang)
                guiDi.push(goi('editMessageText', { chat_id: t.chatId, message_id: t.messageId,
                                                    text: t.text + `\n\n✅ Đã xử lý: ${ai} lúc ${gio(now)}` }));
            }
            sql.push({ topic: 'UPDATE su_kien SET xac_nhan_boi = $1, xac_nhan_luc = $2 WHERE ma_phong = $3 AND bat_dau = $4 AND xac_nhan_boi IS NULL',
                       payload: [ai, now, ma, Number(batDau)], muc: 'su_kien' });
            sql.push({ topic: 'INSERT INTO nhat_ky (thoi_gian, ma_phong, ma_thiet_bi, loai, tu, den, nhiet_do, ghi_chu) VALUES ($1, $2, NULL, $3, NULL, NULL, NULL, $4)',
                       payload: [now, ma, 'xac_nhan', 'Telegram: ' + ai + ' bấm Đã xử lý'], muc: 'nk_ghi' });
            node.status({ fill: 'green', shape: 'dot', text: `phòng ${ma} xác nhận bởi ${ai}` });
            continue;
        }
        const m = u.message;
        if (!m || typeof m.text !== 'string') continue;
        const chat = String(m.chat.id);
        if (!DUOC_PHEP.includes(chat)) { node.warn('Bỏ qua lệnh từ chat không có quyền: ' + chat); continue; }
        const lenh = m.text.trim().split(/[\s@]/)[0].toLowerCase();
        if (lenh === '/trangthai') {
            const st = global.get('trangThaiPhong');
            let text;
            if (!st) text = 'Chưa có dữ liệu.';
            else {
                const t = st.tongHop;
                const nang = st.phong.filter(p => p.trangThai !== 'BÌNH THƯỜNG')
                    .map(p => `• ${p.ma}: ${p.trangThai}` + (p.nhietDo !== null ? ` (${p.nhietDo.toFixed(1)} °C)` : '') +
                              (p.khoi ? ' 💨' : '') + (p.ngatDien ? ' 🔌' : '') + (p.tatTieng ? ' 🔕' : ''));
                text = `📋 Trạng thái lúc ${gio(st.luc)}\nNguy hiểm ${t.nguyHiem} · Báo động ${t.baoDong} · Chú ý ${t.chuY} · ` +
                       `Lỗi ${t.loi} · Mất kết nối ${t.matKetNoi} · Bình thường ${t.binhThuong}` +
                       (nang.length ? '\n\n' + nang.join('\n') : '\n\nTất cả phòng bình thường ✅');
            }
            guiDi.push(goi('sendMessage', { chat_id: m.chat.id, text }));
        } else if (lenh === '/lichsu') {
            sql.push({ topic: 'SELECT ma_phong, bat_dau, ket_thuc, nhiet_do_max, muc_max, xac_nhan_boi FROM su_kien ORDER BY bat_dau DESC LIMIT 5',
                       payload: [], muc: 'tg_lichsu', chatId: m.chat.id });
        } else if (lenh.startsWith('/')) {
            guiDi.push(goi('sendMessage', { chat_id: m.chat.id,
                text: 'Lệnh hỗ trợ:\n/trangthai - tình trạng 20 phòng\n/lichsu - 5 đợt báo động gần nhất\nKhi có báo động, bấm "✅ Đã xử lý" dưới tin để xác nhận.' }));
        }
    }
    flow.set('tgOffset', offset);
}
flow.set('tgCho', cho);
return [guiDi.length ? guiDi : null, sql.length ? sql : null];
"""

FN_TG_LICHSU = r"""
// Trả lời lệnh /lichsu từ kết quả SQLite
const API = env.get('TELEGRAM_API') || 'https://api.telegram.org';
const token = env.get('TELEGRAM_TOKEN');
if (!token) return null;
const ngay = ms => new Date(ms).toLocaleString('vi-VN', { hour12: false, timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
const rows = msg.payload || [];
const dong = rows.map(r => `• ${r.ma_phong} ${ngay(r.bat_dau)} → ${r.ket_thuc ? ngay(r.ket_thuc) : 'ĐANG báo động'}` +
    `, max ${r.nhiet_do_max === null ? '--' : r.nhiet_do_max.toFixed(1) + ' °C'}` + ((r.muc_max || 2) >= 3 ? ', NGUY HIỂM' : '') +
    (r.xac_nhan_boi ? `, xác nhận: ${r.xac_nhan_boi}` : ''));
return { method: 'POST', url: `${API}/bot${token}/sendMessage`, headers: { 'Content-Type': 'application/json' },
         payload: { chat_id: msg.chatId, text: rows.length ? '🗂 5 đợt báo động gần nhất\n' + dong.join('\n') : 'Chưa có đợt báo động nào.' },
         tg: { loai: 'sendMessage' } };
"""

FN_CT_TRUY_VAN = r"""
// MR-11: trang Chi tiết phòng. Nhận mã phòng khi bấm trên sơ đồ / nút chuyển phòng; tự làm mới mỗi 3 s.
if (msg.muc === 'chi_tiet' && typeof msg.payload === 'string') global.set('phongChiTiet', msg.payload);
const ma = global.get('phongChiTiet') || '101';
const tu = Date.now() - 30 * 60 * 1000;
return { topic: 'SELECT thoi_gian, nhiet_do FROM do_nhiet WHERE ma_phong = $1 AND thoi_gian >= $2 ORDER BY thoi_gian',
         payload: [ma, tu], muc: 'ct_nhiet', phong: ma, tu };
"""

FN_CT_SU_KIEN = r"""
msg.diem = (msg.payload || []).map(r => [r.thoi_gian, r.nhiet_do]);
msg.topic = 'SELECT id, ma_phong, bat_dau, ket_thuc, nhiet_do_max, muc_max, co_khoi, ngat_dien, xac_nhan_boi, xac_nhan_luc FROM su_kien WHERE ma_phong = $1 ORDER BY bat_dau DESC LIMIT 10';
msg.payload = [msg.phong];
msg.muc = 'ct_sukien';
return msg;
"""

FN_CT_NHAT_KY = r"""
msg.suKien = msg.payload || [];
const st = global.get('trangThaiPhong');
const p = st ? st.phong.find(x => x.ma === msg.phong) : null;
msg.topic = 'SELECT id, thoi_gian, ma_phong, ma_thiet_bi, loai, tu, den, nhiet_do, ghi_chu FROM nhat_ky ' +
            'WHERE ma_phong = $1 OR (ma_phong IS NULL AND ma_thiet_bi = $2) ORDER BY thoi_gian DESC, id DESC LIMIT 20';
msg.payload = [msg.phong, p ? p.ma_thiet_bi : ''];
msg.muc = 'ct_nk';
return msg;
"""

FN_CT_GHEP = r"""
const st = global.get('trangThaiPhong');
const p = st ? st.phong.find(x => x.ma === msg.phong) : null;
return { payload: { phong: msg.phong, tt: p || null, diem: msg.diem || [], tu: msg.tu, den: Date.now(),
                    suKien: msg.suKien || [], nhatKy: msg.payload || [], dsPhong: st ? st.phong.map(x => x.ma) : [] } };
"""

FN_CT_DIEU_HUONG = r"""
// Nút trên trang Chi tiết phòng: quay lại sơ đồ (chỉ trình duyệt bấm) hoặc chuyển sang phòng khác
if (msg.muc === 'quay_lai') return [{ payload: { page: 'Bảng điều khiển' }, _client: msg._client }, null];
if (msg.muc === 'chi_tiet') return [null, msg];
return null;
"""

TPL_CHI_TIET = r"""<template>
  <div class="ct" v-if="d">
    <div class="thanh">
      <button class="nut" @click="quayLai">← Sơ đồ</button>
      <button class="nut" @click="chuyen(-1)" :disabled="!d.dsPhong.length">‹</button>
      <select v-model="chon" @change="mo(chon)">
        <option v-for="m in d.dsPhong" :key="m" :value="m">Phòng {{ m }}</option>
      </select>
      <button class="nut" @click="chuyen(1)" :disabled="!d.dsPhong.length">›</button>
    </div>

    <div :class="['dau', lop]">
      <div>
        <div class="ten">Phòng {{ d.phong }}</div>
        <div class="tt">{{ tt ? tt.trangThai : 'Chưa có dữ liệu' }}</div>
        <div class="ghi" v-if="tt && tt.ghiChu">{{ tt.ghiChu }}</div>
      </div>
      <div class="nhiet">{{ tt && tt.nhietDo !== null ? tt.nhietDo.toFixed(1) + ' °C' : '--' }}</div>
    </div>

    <div class="the-hang">
      <div class="the"><span>Cảm biến khói</span><b :class="{ xau: tt && tt.khoi }">{{ tt ? (tt.khoi ? '💨 CÓ KHÓI' : 'Không khói') : '--' }}</b></div>
      <div class="the"><span>Điện phòng</span><b :class="{ xau: tt && tt.ngatDien }">{{ tt ? (tt.ngatDien ? '🔌 ĐÃ NGẮT' : 'Đang có điện') : '--' }}</b></div>
      <div class="the"><span>Còi</span><b>{{ tt ? (tt.tatTieng ? '🔕 Đang tắt tiếng' : 'Bình thường') : '--' }}</b></div>
      <div class="the"><span>Cảm biến nhiệt</span><b :class="{ xau: tt && tt.loi }">{{ tt ? (tt.loi ? '⚠️ Lỗi' : 'Hoạt động') : '--' }}</b></div>
    </div>

    <div class="khoi">
      <div class="tieu-de">Nhiệt độ 30 phút gần nhất ({{ d.diem.length }} điểm)</div>
      <svg viewBox="0 0 800 240" class="bd">
        <g v-for="v in vachY" :key="'y' + v">
          <line :x1="L" :x2="R" :y1="y(v)" :y2="y(v)" class="luoi" />
          <text :x="L - 6" :y="y(v) + 4" text-anchor="end" class="chu">{{ v }}</text>
        </g>
        <g v-for="m in vachX" :key="'x' + m.t"><text :x="x(m.t)" :y="B + 18" text-anchor="middle" class="chu">{{ m.nhan }}</text></g>
        <line :x1="L" :x2="R" :y1="y(45)" :y2="y(45)" class="ng bat" />
        <line :x1="L" :x2="R" :y1="y(40)" :y2="y(40)" class="ng tat" />
        <line :x1="L" :x2="R" :y1="y(38)" :y2="y(38)" class="ng cy" />
        <polyline v-if="d.diem.length > 1" :points="duong" class="duong" />
        <text v-if="!d.diem.length" x="400" y="120" text-anchor="middle" class="chu">Chưa có dữ liệu</text>
      </svg>
    </div>

    <div class="khoi">
      <div class="tieu-de">Các đợt báo động của phòng (10 gần nhất)</div>
      <table v-if="d.suKien.length">
        <tr><th>Bắt đầu</th><th>Kết thúc</th><th>Cao nhất</th><th>Cấp</th><th>Khói</th><th>Ngắt điện</th><th>Xác nhận</th></tr>
        <tr v-for="r in d.suKien" :key="r.id" :class="{ mo: r.ket_thuc === null }">
          <td>{{ ngayGio(r.bat_dau) }}</td>
          <td>{{ r.ket_thuc === null ? 'đang báo động' : ngayGio(r.ket_thuc) }}</td>
          <td>{{ r.nhiet_do_max === null ? '--' : r.nhiet_do_max.toFixed(1) + ' °C' }}</td>
          <td>{{ (r.muc_max || 2) >= 3 ? 'NGUY HIỂM' : 'BÁO ĐỘNG' }}</td>
          <td>{{ r.co_khoi ? '💨' : '-' }}</td><td>{{ r.ngat_dien ? '🔌' : '-' }}</td>
          <td>{{ r.xac_nhan_boi || (r.ket_thuc === null ? 'chưa' : '-') }}</td>
        </tr>
      </table>
      <div v-else class="chu-xam">Phòng này chưa có đợt báo động nào.</div>
    </div>

    <div class="khoi">
      <div class="tieu-de">Nhật ký trạng thái (20 thay đổi gần nhất)</div>
      <table v-if="d.nhatKy && d.nhatKy.length">
        <tr><th>Lúc</th><th>Loại</th><th>Thay đổi</th><th>Nhiệt độ</th><th>Ghi chú</th></tr>
        <tr v-for="r in d.nhatKy" :key="'nk' + r.id">
          <td>{{ ngayGio(r.thoi_gian) }}</td>
          <td><span :class="['nk-loai', r.loai]">{{ tenLoai(r.loai) }}</span></td>
          <td><template v-if="r.tu || r.den"><span :class="['tt-chip', lopTT(r.tu)]">{{ r.tu }}</span> → <span :class="['tt-chip', lopTT(r.den)]">{{ r.den }}</span></template></td>
          <td>{{ r.nhiet_do === null ? '' : r.nhiet_do.toFixed(1) + ' °C' }}</td>
          <td>{{ r.ma_phong ? (r.ghi_chu || '') : '(cả tầng ' + r.ma_thiet_bi + ') ' + (r.ghi_chu || '') }}</td>
        </tr>
      </table>
      <div v-else class="chu-xam">Chưa có thay đổi nào được ghi.</div>
    </div>

    <div class="khoi thiet-bi" v-if="tt">
      <div class="tieu-de">Thiết bị</div>
      <div>Mã thiết bị: <b>{{ tt.ma_thiet_bi }}</b> · seq: {{ tt.seq === null ? '--' : tt.seq }} · tin mất: {{ tt.tinMat }}</div>
      <div>Tin cuối: {{ tt.capNhat ? gio(tt.capNhat) : 'chưa có' }}
        <span v-if="tt.lechGio !== null"> · giờ thiết bị (NTP) lệch {{ tt.lechGio }} s</span>
        <span v-else> · thiết bị chưa đồng bộ giờ NTP</span></div>
      <div v-if="tt.khoiDongLai">Khởi động lại lúc {{ gio(tt.khoiDongLai) }}</div>
    </div>
  </div>
  <div v-else class="chu-xam">Chọn một phòng trên sơ đồ mặt bằng để xem chi tiết.</div>
</template>

<script>
export default {
  data() { return { chon: '', L: 44, R: 780, T: 12, B: 208 }; },
  computed: {
    d() { return (this.msg && this.msg.payload && this.msg.payload.phong) ? this.msg.payload : null; },
    tt() { return this.d ? this.d.tt : null; },
    lop() {
      const t = this.tt ? this.tt.trangThai : '';
      return { 'BÌNH THƯỜNG': 'bt', 'CHÚ Ý': 'cy', 'BÁO ĐỘNG': 'bdg', 'NGUY HIỂM': 'nh', 'LỖI CẢM BIẾN': 'loi', 'MẤT KẾT NỐI': 'mat' }[t] || 'mat';
    },
    yMin() { return Math.floor(Math.min(20, ...this.d.diem.map(p => p[1])) / 5) * 5; },
    yMax() { return Math.ceil(Math.max(50, ...this.d.diem.map(p => p[1])) / 5) * 5; },
    vachY() { const a = []; for (let v = this.yMin; v <= this.yMax; v += 5) a.push(v); return a; },
    vachX() {
      const a = [], buoc = 5 * 60000;
      for (let t = Math.ceil(this.d.tu / buoc) * buoc; t <= this.d.den; t += buoc)
        a.push({ t, nhan: new Date(t).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false }) });
      return a;
    },
    duong() { return this.d.diem.map(p => this.x(p[0]).toFixed(1) + ',' + this.y(p[1]).toFixed(1)).join(' '); }
  },
  watch: { d(v) { if (v) this.chon = v.phong; } },
  methods: {
    x(t) { return this.L + (t - this.d.tu) / Math.max(1, this.d.den - this.d.tu) * (this.R - this.L); },
    y(v) { return this.B - (v - this.yMin) / Math.max(1, this.yMax - this.yMin) * (this.B - this.T); },
    gio(ms) { return new Date(ms).toLocaleTimeString('vi-VN', { hour12: false }); },
    ngayGio(ms) { return new Date(ms).toLocaleString('vi-VN', { hour12: false, day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }); },
    lopTT(t) { return { 'BÌNH THƯỜNG': 'bt', 'CHÚ Ý': 'cy', 'BÁO ĐỘNG': 'bd', 'NGUY HIỂM': 'nh', 'LỖI CẢM BIẾN': 'loi', 'MẤT KẾT NỐI': 'mat' }[t] || ''; },
    tenLoai(l) { return { trang_thai: 'Trạng thái', dien: 'Điện', tat_tieng: 'Tắt tiếng', khoi_dong_lai: 'Khởi động lại', xac_nhan: 'Xác nhận' }[l] || l; },
    mo(ma) { this.send({ payload: ma, muc: 'chi_tiet' }); },
    chuyen(b) {
      const ds = this.d.dsPhong, i = ds.indexOf(this.d.phong);
      this.mo(ds[(i + b + ds.length) % ds.length]);
    },
    quayLai() { this.send({ muc: 'quay_lai' }); }
  }
}
</script>

<style scoped>
.ct { width: 100%; font-family: system-ui, sans-serif; }
.thanh { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
.nut { padding: 6px 12px; border: 1px solid #90a4ae; background: #fff; border-radius: 6px; cursor: pointer; font-size: 15px; }
.nut:hover { background: #eceff1; }
select { padding: 6px 8px; font-size: 15px; border: 1px solid #90a4ae; border-radius: 6px; background: #fff; }
.dau { display: flex; justify-content: space-between; align-items: center; border-radius: 10px; padding: 14px 18px; border: 3px solid; margin-bottom: 10px; }
.dau.bt { background: #e8f5e9; border-color: #66bb6a; color: #1b5e20; }
.dau.cy { background: #fff59d; border-color: #f9a825; color: #6d4c00; }
.dau.bdg { background: #ffcdd2; border-color: #c62828; color: #b71c1c; }
.dau.nh { background: #7f0000; border-color: #ff1744; color: #fff; animation: nh .5s infinite; }
.dau.loi { background: #e1bee7; border-color: #8e24aa; color: #4a148c; }
.dau.mat { background: #eceff1; border-color: #90a4ae; color: #455a64; }
@keyframes nh { 50% { background: #d50000; } }
.ten { font-size: 15px; font-weight: 600; }
.tt { font-size: 26px; font-weight: 800; }
.ghi { font-size: 14px; }
.nhiet { font-size: 44px; font-weight: 800; }
.the-hang { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin-bottom: 10px; }
@media (max-width: 700px) { .the-hang { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.the { background: #fff; border: 1px solid #cfd8dc; border-radius: 8px; padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
.the span { color: #607d8b; font-size: 12px; }
.the b.xau { color: #b71c1c; }
.khoi { background: #fff; border: 1px solid #cfd8dc; border-radius: 8px; padding: 10px; margin-bottom: 10px; overflow-x: auto; }
.tieu-de { font-weight: 700; color: #37474f; margin-bottom: 6px; }
.bd { width: 100%; height: auto; }
.luoi { stroke: #eceff1; } .chu { fill: #607d8b; font-size: 12px; }
.ng { stroke-width: 1.5; stroke-dasharray: 6 4; } .ng.bat { stroke: #c62828; } .ng.tat { stroke: #f9a825; } .ng.cy { stroke: #8d6e00; stroke-dasharray: 2 4; }
.duong { fill: none; stroke: #1565c0; stroke-width: 2; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: #455a64; border-bottom: 2px solid #cfd8dc; padding: 4px 6px; }
td { border-bottom: 1px solid #eceff1; padding: 4px 6px; }
tr.mo td { background: #ffebee; color: #b71c1c; font-weight: 600; }
.thiet-bi { font-size: 14px; color: #37474f; line-height: 1.7; }
.nk-loai { padding: 1px 6px; border-radius: 8px; font-size: 12px; font-weight: 600; background: #eceff1; color: #37474f; white-space: nowrap; }
.nk-loai.dien { background: #fff3e0; color: #e65100; } .nk-loai.tat_tieng { background: #ede7f6; color: #4527a0; }
.nk-loai.xac_nhan { background: #e8f5e9; color: #1b5e20; } .nk-loai.khoi_dong_lai { background: #e3f2fd; color: #0d47a1; }
.tt-chip { font-weight: 700; } .tt-chip.bt { color: #1b5e20; } .tt-chip.cy { color: #8d6e00; } .tt-chip.bd { color: #b71c1c; }
.tt-chip.nh { color: #fff; background: #7f0000; padding: 0 4px; border-radius: 4px; } .tt-chip.loi { color: #6a1b9a; } .tt-chip.mat { color: #546e7a; }

.chu-xam { color: #607d8b; }
</style>
"""

TPL_BIEU_DO = r"""<template>
  <div class="bd">
    <div class="hang">
      <label>Phòng
        <select v-model="phong" @change="chon">
          <option v-for="p in dsPhong" :key="p" :value="p">{{ p }}</option>
        </select>
      </label>
      <span class="ghi">30 phút gần nhất · {{ soDiem }} điểm · nét đứt: báo động 45 °C / tắt 40 °C / chú ý 38 °C</span>
    </div>
    <svg viewBox="0 0 800 280" class="khung" role="img" :aria-label="'Nhiệt độ phòng ' + phong">
      <g v-for="v in vachY" :key="'y' + v">
        <line :x1="L" :x2="R" :y1="y(v)" :y2="y(v)" class="luoi" />
        <text :x="L - 6" :y="y(v) + 4" text-anchor="end" class="chu">{{ v }}</text>
      </g>
      <g v-for="m in vachX" :key="'x' + m.t">
        <text :x="x(m.t)" :y="B + 18" text-anchor="middle" class="chu">{{ m.nhan }}</text>
      </g>
      <line :x1="L" :x2="R" :y1="y(45)" :y2="y(45)" class="nguong bat" />
      <line :x1="L" :x2="R" :y1="y(40)" :y2="y(40)" class="nguong tat" />
      <line :x1="L" :x2="R" :y1="y(38)" :y2="y(38)" class="nguong cy" />
      <polyline v-if="soDiem > 1" :points="duong" class="duong" />
      <circle v-if="diemCuoi" :cx="x(diemCuoi[0])" :cy="y(diemCuoi[1])" r="4" class="cham" />
      <text v-if="diemCuoi" :x="x(diemCuoi[0]) - 8" :y="y(diemCuoi[1]) - 10" text-anchor="end" class="gia-tri">{{ diemCuoi[1].toFixed(1) }} °C</text>
      <text v-if="soDiem === 0" x="400" y="140" text-anchor="middle" class="chu">Chưa có dữ liệu cho phòng này</text>
    </svg>
  </div>
</template>

<script>
export default {
  data() {
    return { phong: '101', dsPhong: DS_PHONG, L: 48, R: 780, T: 16, B: 244 };
  },
  computed: {
    d() { return (this.msg && this.msg.payload && this.msg.payload.diem) ? this.msg.payload : null; },
    soDiem() { return this.d ? this.d.diem.length : 0; },
    tu() { return this.d ? this.d.tu : Date.now() - 1800000; },
    den() { return this.d ? this.d.den : Date.now(); },
    yMin() { const v = this.d ? this.d.diem.map(p => p[1]) : []; return Math.floor(Math.min(20, ...v) / 5) * 5; },
    yMax() { const v = this.d ? this.d.diem.map(p => p[1]) : []; return Math.ceil(Math.max(50, ...v) / 5) * 5; },
    vachY() { const a = []; for (let v = this.yMin; v <= this.yMax; v += 5) a.push(v); return a; },
    vachX() {
      const a = [];
      const buoc = 5 * 60000;
      for (let t = Math.ceil(this.tu / buoc) * buoc; t <= this.den; t += buoc) {
        a.push({ t, nhan: new Date(t).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false }) });
      }
      return a;
    },
    duong() { return this.d.diem.map(p => this.x(p[0]).toFixed(1) + ',' + this.y(p[1]).toFixed(1)).join(' '); },
    diemCuoi() { return this.soDiem ? this.d.diem[this.soDiem - 1] : null; }
  },
  watch: {
    msg(m) { if (m && m.payload && m.payload.phong) this.phong = m.payload.phong; }
  },
  methods: {
    x(t) { return this.L + (t - this.tu) / Math.max(1, this.den - this.tu) * (this.R - this.L); },
    y(v) { return this.B - (v - this.yMin) / Math.max(1, this.yMax - this.yMin) * (this.B - this.T); },
    chon() { this.send({ payload: this.phong, muc: 'chon_phong' }); }
  }
}
</script>

<style scoped>
.bd { width: 100%; font-family: system-ui, sans-serif; }
.hang { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 6px; }
select { margin-left: 6px; padding: 4px 8px; font-size: 15px; border: 1px solid #90a4ae; border-radius: 4px; background: #fff; }
.ghi { color: #607d8b; font-size: 13px; }
.khung { width: 100%; height: auto; }
.luoi { stroke: #eceff1; }
.chu { fill: #607d8b; font-size: 12px; }
.nguong { stroke-width: 1.5; stroke-dasharray: 6 4; }
.nguong.bat { stroke: #c62828; }
.nguong.tat { stroke: #f9a825; }
.nguong.cy { stroke: #8d6e00; stroke-dasharray: 2 4; }
.duong { fill: none; stroke: #1565c0; stroke-width: 2; }
.cham { fill: #1565c0; }
.gia-tri { fill: #0d47a1; font-size: 13px; font-weight: 600; }
</style>
""".replace("DS_PHONG", json.dumps(TAT_CA_PHONG))

TPL_SU_KIEN = r"""<template>
  <div class="sk">
    <table v-if="ds.length">
      <thead>
        <tr><th>Phòng</th><th>Bắt đầu</th><th>Kết thúc</th><th>Kéo dài</th><th>Cao nhất</th><th>Cấp</th><th>Khói</th><th>Ngắt điện</th><th>Xác nhận</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in ds" :key="r.id" :class="{ mo: r.ket_thuc === null }">
          <td class="ma">{{ r.ma_phong }}</td>
          <td>{{ ngayGio(r.bat_dau) }}</td>
          <td>{{ r.ket_thuc === null ? 'đang báo động' : ngayGio(r.ket_thuc) }}</td>
          <td>{{ keoDai(r) }}</td>
          <td>{{ r.nhiet_do_max === null ? '--' : r.nhiet_do_max.toFixed(1) + ' °C' }}</td>
          <td><span :class="['cap', 'c' + (r.muc_max || 2)]">{{ (r.muc_max || 2) >= 3 ? 'NGUY HIỂM' : 'BÁO ĐỘNG' }}</span></td>
          <td>{{ r.co_khoi ? '💨 có' : '-' }}</td>
          <td>{{ r.ngat_dien ? '🔌 có' : '-' }}</td>
          <td>{{ r.xac_nhan_boi ? r.xac_nhan_boi + ' · ' + gioNgan(r.xac_nhan_luc) : (r.ket_thuc === null ? 'chưa' : '-') }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="trong">Chưa có đợt báo động nào.</div>
  </div>
</template>

<script>
export default {
  computed: {
    ds() { return (this.msg && Array.isArray(this.msg.payload)) ? this.msg.payload : []; }
  },
  methods: {
    ngayGio(ms) {
      return new Date(ms).toLocaleString('vi-VN', { hour12: false, day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    },
    gioNgan(ms) { return ms ? new Date(ms).toLocaleTimeString('vi-VN', { hour12: false, hour: '2-digit', minute: '2-digit' }) : ''; },
    keoDai(r) {
      const s = Math.round(((r.ket_thuc === null ? Date.now() : r.ket_thuc) - r.bat_dau) / 1000);
      return s < 60 ? s + ' s' : Math.floor(s / 60) + ' ph ' + (s % 60) + ' s';
    }
  }
}
</script>

<style scoped>
.sk { width: 100%; font-family: system-ui, sans-serif; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; color: #455a64; border-bottom: 2px solid #cfd8dc; padding: 6px 8px; }
td { border-bottom: 1px solid #eceff1; padding: 6px 8px; }
tr.mo td { background: #ffebee; color: #b71c1c; font-weight: 600; }
.ma { font-weight: 700; }
.trong { color: #607d8b; }
.cap { padding: 1px 6px; border-radius: 8px; font-size: 12px; font-weight: 700; }
.cap.c2 { background: #ffcdd2; color: #b71c1c; }
.cap.c3 { background: #7f0000; color: #fff; }
</style>
"""

TPL_NHAT_KY = r"""<template>
  <div class="nk">
    <div class="loc">
      <label>Phòng
        <select v-model="phong" @change="loc">
          <option value="">Tất cả</option>
          <option v-for="p in dsPhong" :key="p" :value="p">{{ p }}</option>
        </select>
      </label>
      <label>Ngày <input type="date" v-model="ngay" @change="loc" /></label>
      <label>Loại
        <select v-model="loai" @change="loc">
          <option value="">Tất cả</option>
          <option value="trang_thai">Trạng thái</option><option value="dien">Điện</option>
          <option value="tat_tieng">Tắt tiếng</option><option value="khoi_dong_lai">Khởi động lại</option>
          <option value="xac_nhan">Xác nhận</option>
        </select>
      </label>
      <button class="nut" @click="homNay">Hôm nay</button>
      <span class="ghi">{{ ds.length }} dòng{{ ds.length >= 300 ? ' (300 mới nhất)' : '' }}</span>
    </div>
    <table v-if="ds.length">
      <thead><tr><th>Lúc</th><th>Phòng</th><th>Loại</th><th>Thay đổi</th><th>Nhiệt độ</th><th>Ghi chú</th></tr></thead>
      <tbody>
        <tr v-for="r in ds" :key="r.id">
          <td>{{ ngayGio(r.thoi_gian) }}</td>
          <td class="ma">{{ r.ma_phong || ('tầng ' + r.ma_thiet_bi) }}</td>
          <td><span :class="['nk-loai', r.loai]">{{ tenLoai(r.loai) }}</span></td>
          <td><template v-if="r.tu || r.den"><span :class="['tt-chip', lopTT(r.tu)]">{{ r.tu }}</span> → <span :class="['tt-chip', lopTT(r.den)]">{{ r.den }}</span></template></td>
          <td>{{ r.nhiet_do === null ? '' : r.nhiet_do.toFixed(1) + ' °C' }}</td>
          <td>{{ r.ghi_chu }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="trong">Không có thay đổi nào khớp bộ lọc.</div>
  </div>
</template>

<script>
export default {
  data() { return { phong: '', ngay: '', loai: '', dsPhong: DS_PHONG_JSON }; },
  computed: {
    ds() { return (this.msg && this.msg.payload && Array.isArray(this.msg.payload.dong)) ? this.msg.payload.dong : []; }
  },
  watch: {
    msg(m) { if (m && m.payload && m.payload.loc) { const l = m.payload.loc; this.phong = l.phong || ''; this.ngay = l.ngay || ''; this.loai = l.loai || ''; } }
  },
  methods: {
    loc() { this.send({ muc: 'loc_nk', payload: { phong: this.phong, ngay: this.ngay, loai: this.loai } }); },
    homNay() {
      const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
      this.ngay = d.toISOString().slice(0, 10); this.loc();
    },
    lopTT(t) { return { 'BÌNH THƯỜNG': 'bt', 'CHÚ Ý': 'cy', 'BÁO ĐỘNG': 'bd', 'NGUY HIỂM': 'nh', 'LỖI CẢM BIẾN': 'loi', 'MẤT KẾT NỐI': 'mat' }[t] || ''; },
    tenLoai(l) { return { trang_thai: 'Trạng thái', dien: 'Điện', tat_tieng: 'Tắt tiếng', khoi_dong_lai: 'Khởi động lại', xac_nhan: 'Xác nhận' }[l] || l; },
    ngayGio(ms) { return new Date(ms).toLocaleString('vi-VN', { hour12: false, day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
  }
}
</script>

<style scoped>
.nk { width: 100%; font-family: system-ui, sans-serif; overflow-x: auto; }
.loc { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 8px; font-size: 14px; }
select, input { margin-left: 6px; padding: 4px 8px; font-size: 14px; border: 1px solid #90a4ae; border-radius: 4px; background: #fff; }
.nut { padding: 4px 10px; border: 1px solid #90a4ae; background: #fff; border-radius: 4px; cursor: pointer; }
.ghi { color: #607d8b; font-size: 13px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: #455a64; border-bottom: 2px solid #cfd8dc; padding: 5px 8px; }
td { border-bottom: 1px solid #eceff1; padding: 5px 8px; }
.ma { font-weight: 700; }
.trong { color: #607d8b; }

.nk-loai { padding: 1px 6px; border-radius: 8px; font-size: 12px; font-weight: 600; background: #eceff1; color: #37474f; white-space: nowrap; }
.nk-loai.dien { background: #fff3e0; color: #e65100; } .nk-loai.tat_tieng { background: #ede7f6; color: #4527a0; }
.nk-loai.xac_nhan { background: #e8f5e9; color: #1b5e20; } .nk-loai.khoi_dong_lai { background: #e3f2fd; color: #0d47a1; }
.tt-chip { font-weight: 700; } .tt-chip.bt { color: #1b5e20; } .tt-chip.cy { color: #8d6e00; } .tt-chip.bd { color: #b71c1c; }
.tt-chip.nh { color: #fff; background: #7f0000; padding: 0 4px; border-radius: 4px; } .tt-chip.loi { color: #6a1b9a; } .tt-chip.mat { color: #546e7a; }
</style>
"""

FN_NK_TRUY_VAN = r"""
// MR-16: bảng nhật ký trang Lịch sử. Bộ lọc nhận từ khung nhật ký; tự làm mới mỗi 5 s với bộ lọc đang chọn.
if (msg.muc === 'loc_nk' && msg.payload && typeof msg.payload === 'object') flow.set('locNhatKy', msg.payload);
const loc = flow.get('locNhatKy') || { phong: '', ngay: '', loai: '' };
const dk = [], ts = [];
if (loc.phong) { ts.push(loc.phong); dk.push(`ma_phong = $${ts.length}`); }
if (loc.loai) { ts.push(loc.loai); dk.push(`loai = $${ts.length}`); }
if (loc.ngay) {                                   // ngày theo giờ Việt Nam
    const dau = new Date(loc.ngay + 'T00:00:00+07:00').getTime();
    ts.push(dau); dk.push(`thoi_gian >= $${ts.length}`);
    ts.push(dau + 24 * 3600 * 1000); dk.push(`thoi_gian < $${ts.length}`);
}
return { topic: 'SELECT id, thoi_gian, ma_phong, ma_thiet_bi, loai, tu, den, nhiet_do, ghi_chu FROM nhat_ky' +
                (dk.length ? ' WHERE ' + dk.join(' AND ') : '') + ' ORDER BY thoi_gian DESC, id DESC LIMIT 300',
         payload: ts, muc: 'nk_bang', loc };
"""

TPL_NHAT_KY = TPL_NHAT_KY.replace("DS_PHONG_JSON", json.dumps(TAT_CA_PHONG))

FN_NK_DINH_DANG = r"""
return { payload: { dong: msg.payload || [], loc: msg.loc } };
"""

TAB_LS = "cbc_tab_ls"


def fn(id_, ten, code, outputs, x, y, wires, nhan=None):
    n = {"id": id_, "type": "function", "z": TAB_LS, "name": ten, "func": code, "outputs": outputs,
         "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [], "x": x, "y": y, "wires": wires}
    if nhan:
        n["outputLabels"] = nhan
    return n


def inject(id_, ten, x, y, wires, repeat="", once=True, delay="0.2"):
    return {"id": id_, "type": "inject", "z": TAB_LS, "name": ten, "props": [{"p": "payload"}],
            "repeat": repeat, "crontab": "", "once": once, "onceDelay": delay, "topic": "",
            "payload": "", "payloadType": "date", "x": x, "y": y, "wires": wires}


SQL = "cbc_ls_sqlite"
LICH_SU = [
    {"id": TAB_LS, "type": "tab", "label": "LichSu", "disabled": False,
     "info": "Task 3 - SRS CanhBaoChay v1.2 mục 3.4, 7.4, 10.\nSQLite: su_kien, do_nhiet. Trang Chi tiết phòng.\nTelegram 2 chiều: đặt biến môi trường của tab (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_CHAT_ID_2 tuỳ chọn).",
     "env": [{"name": "TELEGRAM_TOKEN", "value": "", "type": "str"},
             {"name": "TELEGRAM_CHAT_ID", "value": "", "type": "str"},
             {"name": "TELEGRAM_CHAT_ID_2", "value": "", "type": "str"},
             {"name": "TELEGRAM_API", "value": "", "type": "str"}]},
    {"id": "cbc_sqlite_db", "type": "sqlitedb", "db": "canhbaochay.db", "mode": "RWC"},
    {"id": "cbc_page_ls", "type": "ui-page", "name": "Lịch sử", "ui": "cbc_ui_base", "path": "/lichsu",
     "icon": "history", "layout": "grid", "theme": "cbc_ui_theme", "order": 2, "className": "",
     "visible": "true", "disabled": "false"},
    {"id": "cbc_grp_bieudo", "type": "ui-group", "name": "Biểu đồ nhiệt độ", "page": "cbc_page_ls",
     "width": "12", "height": "1", "order": 1, "showTitle": True, "className": "", "visible": "true", "disabled": "false"},
    {"id": "cbc_grp_sukien", "type": "ui-group", "name": "Các đợt báo động (50 đợt mới nhất)", "page": "cbc_page_ls",
     "width": "12", "height": "1", "order": 2, "showTitle": True, "className": "", "visible": "true", "disabled": "false"},
    {"id": "cbc_grp_nk", "type": "ui-group", "name": "Nhật ký trạng thái", "page": "cbc_page_ls",
     "width": "12", "height": "1", "order": 3, "showTitle": True, "className": "", "visible": "true", "disabled": "false"},
    {"id": "cbc_page_ct", "type": "ui-page", "name": "Chi tiết phòng", "ui": "cbc_ui_base", "path": "/chitiet",
     "icon": "door", "layout": "grid", "theme": "cbc_ui_theme", "order": 3, "className": "",
     "visible": "true", "disabled": "false"},
    {"id": "cbc_grp_ct", "type": "ui-group", "name": "Chi tiết phòng", "page": "cbc_page_ct",
     "width": "12", "height": "1", "order": 1, "showTitle": False, "className": "", "visible": "true", "disabled": "false"},

    # Khởi tạo CSDL
    inject("cbc_ls_inject_kt", "Khởi động", 130, 60, [["cbc_ls_fn_kt"]], delay="0.1"),
    fn("cbc_ls_fn_kt", "Tạo bảng (tuần tự)", FN_KHOI_TAO, 1, 340, 60, [[SQL]]),

    # Dữ liệu MQTT -> đợt báo động
    {"id": "cbc_ls_mqtt_in", "type": "mqtt in", "z": TAB_LS, "name": "Dữ liệu phòng",
     "topic": f"{TIEN_TO_TOPIC}/phong/+/dulieu", "qos": "0", "datatype": "json", "broker": "cbc_broker",
     "nl": False, "rap": True, "rh": 0, "inputs": 0, "x": 130, "y": 140, "wires": [["cbc_ls_fn_dot"]]},
    fn("cbc_ls_fn_dot", "Phát hiện đợt (LS-02)", FN_PHAT_HIEN_DOT, 2, 360, 160,
       [[SQL], ["cbc_ls_fn_tg"]], ["SQLite", "Telegram"]),

    # SQLite và phân loại kết quả
    {"id": SQL, "type": "sqlite", "z": TAB_LS, "mydb": "cbc_sqlite_db", "sqlquery": "msg.topic",
     "sql": "", "name": "CSDL lịch sử", "x": 620, "y": 120, "wires": [["cbc_ls_switch"]]},
    {"id": "cbc_ls_switch", "type": "switch", "z": TAB_LS, "name": "Phân loại kết quả", "property": "muc",
     "propertyType": "msg",
     "rules": [{"t": "eq", "v": "khoitao", "vt": "str"}, {"t": "eq", "v": "dot_mo", "vt": "str"},
               {"t": "eq", "v": "su_kien", "vt": "str"}, {"t": "eq", "v": "bang", "vt": "str"},
               {"t": "eq", "v": "bieudo", "vt": "str"}, {"t": "eq", "v": "ct_nhiet", "vt": "str"},
               {"t": "eq", "v": "ct_sukien", "vt": "str"}, {"t": "eq", "v": "tg_lichsu", "vt": "str"},
               {"t": "eq", "v": "ct_nk", "vt": "str"}, {"t": "eq", "v": "nk_bang", "vt": "str"}],
     "checkall": "false", "repair": False, "outputs": 10,
     "outputLabels": ["khoitao", "dot_mo", "su_kien", "bang", "bieudo", "ct_nhiet", "ct_sukien", "tg_lichsu", "ct_nk", "nk_bang"],
     "x": 820, "y": 120,
     "wires": [["cbc_ls_fn_kt"], ["cbc_ls_fn_dotmo"], ["cbc_ls_change_bang"], ["cbc_ls_tpl_sk"], ["cbc_ls_fn_ddbd"],
               ["cbc_ls_fn_ctsk"], ["cbc_ls_fn_ctnk"], ["cbc_ls_fn_tgls"], ["cbc_ls_fn_ctghep"], ["cbc_ls_fn_nkdd"]]},
    fn("cbc_ls_fn_dotmo", "Nạp đợt đang mở", FN_NAP_DOT_MO, 2, 1040, 60,
       [["cbc_ls_fn_dot"], [SQL]], ["xả hàng đợi", "làm mới bảng"]),
    {"id": "cbc_ls_change_bang", "type": "change", "z": TAB_LS, "name": "Truy vấn bảng sự kiện",
     "rules": [{"t": "set", "p": "topic", "pt": "msg",
                "to": "SELECT id, ma_phong, bat_dau, ket_thuc, nhiet_do_max, muc_max, co_khoi, ngat_dien, xac_nhan_boi, xac_nhan_luc FROM su_kien ORDER BY bat_dau DESC LIMIT 50",
                "tot": "str"},
               {"t": "set", "p": "payload", "pt": "msg", "to": "[]", "tot": "json"},
               {"t": "set", "p": "muc", "pt": "msg", "to": "bang", "tot": "str"}],
     "action": "", "property": "", "from": "", "to": "", "reg": False, "x": 1060, "y": 120, "wires": [[SQL]]},
    {"id": "cbc_ls_tpl_sk", "type": "ui-template", "z": TAB_LS, "group": "cbc_grp_sukien", "page": "", "ui": "",
     "name": "Bảng sự kiện (LS-03)", "order": 1, "width": "0", "height": "0", "head": "", "format": TPL_SU_KIEN,
     "storeOutMessages": True, "passthru": False, "resendOnRefresh": True, "templateScope": "local",
     "className": "", "x": 1060, "y": 180, "wires": [[]]},

    # Biểu đồ
    inject("cbc_ls_inject_bd", "Mỗi 5 s", 130, 300, [["cbc_ls_fn_tvbd"]], repeat="5", delay="2"),
    fn("cbc_ls_fn_tvbd", "Truy vấn biểu đồ", FN_TRUY_VAN_BIEU_DO, 1, 340, 300, [[SQL]]),
    fn("cbc_ls_fn_ddbd", "Định dạng biểu đồ", FN_DINH_DANG_BIEU_DO, 1, 1060, 240, [["cbc_ls_tpl_bd"]]),
    {"id": "cbc_ls_tpl_bd", "type": "ui-template", "z": TAB_LS, "group": "cbc_grp_bieudo", "page": "", "ui": "",
     "name": "Biểu đồ nhiệt độ (LS-01)", "order": 1, "width": "0", "height": "0", "head": "", "format": TPL_BIEU_DO,
     "storeOutMessages": True, "passthru": False, "resendOnRefresh": True, "templateScope": "local",
     "className": "", "x": 1300, "y": 240, "wires": [["cbc_ls_fn_tvbd"]]},

    # Dọn dẹp
    inject("cbc_ls_inject_dd", "Mỗi giờ", 130, 380, [["cbc_ls_fn_dd"]], repeat="3600", delay="5"),
    fn("cbc_ls_fn_dd", "Xóa do_nhiet > 24 h, nhật ký > 90 ngày", FN_DON_DEP, 1, 340, 380, [[SQL]]),

    # Nhật ký trạng thái (MR-16)
    {"id": "cbc_ls_link_nk", "type": "link in", "z": TAB_LS, "name": "từ BangDieuKhien: nhật ký",
     "links": ["cbc_bdk_link_nk"], "x": 150, "y": 880, "wires": [[SQL]]},
    inject("cbc_ls_inject_nk", "Mỗi 5 s", 130, 920, [["cbc_ls_fn_nk"]], repeat="5", delay="3"),
    fn("cbc_ls_fn_nk", "Truy vấn nhật ký (lọc)", FN_NK_TRUY_VAN, 1, 360, 920, [[SQL]]),
    fn("cbc_ls_fn_nkdd", "Định dạng nhật ký", FN_NK_DINH_DANG, 1, 1080, 420, [["cbc_ls_tpl_nk"]]),
    {"id": "cbc_ls_tpl_nk", "type": "ui-template", "z": TAB_LS, "group": "cbc_grp_nk", "page": "", "ui": "",
     "name": "Nhật ký trạng thái (MR-16)", "order": 1, "width": "0", "height": "0", "head": "", "format": TPL_NHAT_KY,
     "storeOutMessages": True, "passthru": False, "resendOnRefresh": True, "templateScope": "local",
     "className": "", "x": 1310, "y": 420, "wires": [["cbc_ls_fn_nk"]]},

    # Chi tiết phòng (MR-11)
    {"id": "cbc_ls_link_ct", "type": "link in", "z": TAB_LS, "name": "từ BangDieuKhien: chi tiết",
     "links": ["cbc_bdk_link_ct"], "x": 150, "y": 560, "wires": [["cbc_ls_fn_ct"]]},
    inject("cbc_ls_inject_ct", "Mỗi 3 s", 130, 600, [["cbc_ls_fn_ct"]], repeat="3", delay="3"),
    fn("cbc_ls_fn_ct", "Truy vấn chi tiết", FN_CT_TRUY_VAN, 1, 360, 580, [[SQL]]),
    fn("cbc_ls_fn_ctsk", "Truy vấn sự kiện của phòng", FN_CT_SU_KIEN, 1, 1080, 300, [[SQL]]),
    fn("cbc_ls_fn_ctnk", "Truy vấn nhật ký của phòng", FN_CT_NHAT_KY, 1, 1080, 320, [[SQL]]),
    fn("cbc_ls_fn_ctghep", "Ghép dữ liệu chi tiết", FN_CT_GHEP, 1, 1080, 340, [["cbc_ls_tpl_ct"]]),
    {"id": "cbc_ls_tpl_ct", "type": "ui-template", "z": TAB_LS, "group": "cbc_grp_ct", "page": "", "ui": "",
     "name": "Chi tiết phòng (MR-11)", "order": 1, "width": "0", "height": "0", "head": "", "format": TPL_CHI_TIET,
     "storeOutMessages": True, "passthru": False, "resendOnRefresh": True, "templateScope": "local",
     "className": "", "x": 1310, "y": 340, "wires": [["cbc_ls_fn_dh"]]},
    fn("cbc_ls_fn_dh", "Điều hướng chi tiết", FN_CT_DIEU_HUONG, 2, 1310, 400,
       [["cbc_ls_ctrl"], ["cbc_ls_fn_ct"]], ["quay lại", "đổi phòng"]),
    {"id": "cbc_ls_ctrl", "type": "ui-control", "z": TAB_LS, "name": "Đổi trang", "ui": "cbc_ui_base",
     "events": "all", "x": 1520, "y": 400, "wires": [[]]},

    # Telegram 2 chiều (DB-10, MR-13, MR-14)
    {"id": "cbc_ls_link_tg", "type": "link in", "z": TAB_LS, "name": "từ BangDieuKhien: Telegram",
     "links": ["cbc_bdk_link_tg"], "x": 150, "y": 680, "wires": [["cbc_ls_fn_tg"]]},
    fn("cbc_ls_fn_tg", "Soạn tin Telegram (DB-10)", FN_TELEGRAM, 1, 400, 680, [["cbc_ls_http_tg"]]),
    inject("cbc_ls_inject_poll", "Mỗi 3 s", 130, 740, [["cbc_ls_fn_poll"]], repeat="3", delay="4"),
    fn("cbc_ls_fn_poll", "Hỏi nút bấm / lệnh (getUpdates)", FN_TG_POLL, 1, 400, 740, [["cbc_ls_http_tg"]]),
    inject("cbc_ls_inject_lt", "Mỗi 10 s", 130, 800, [["cbc_ls_fn_lt"]], repeat="10", delay="10"),
    fn("cbc_ls_fn_lt", "Leo thang sau 120 s (MR-14)", FN_TG_LEO_THANG, 1, 400, 800, [["cbc_ls_http_tg"]]),
    {"id": "cbc_ls_http_tg", "type": "http request", "z": TAB_LS, "name": "Telegram API", "method": "use",
     "ret": "obj", "paytoqs": "ignore", "url": "", "tls": "", "persist": False, "proxy": "",
     "insecureHTTPParser": False, "authType": "", "senderr": False, "headers": [], "x": 660, "y": 740,
     "wires": [["cbc_ls_fn_tgkq"]]},
    fn("cbc_ls_fn_tgkq", "Xử lý phản hồi / xác nhận", FN_TG_KET_QUA, 2, 900, 740,
       [["cbc_ls_http_tg"], [SQL]], ["gửi tiếp Telegram", "SQLite"]),
    fn("cbc_ls_fn_tgls", "Trả lời /lichsu", FN_TG_LICHSU, 1, 1080, 380, [["cbc_ls_http_tg"]]),
]


def ghi(ten, nodes):
    (GOC / ten).write_text(json.dumps(nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Da tao nodered/{ten} ({len(nodes)} node)")


if __name__ == "__main__":
    ghi("luong_bangdieukhien.json", BANG_DIEU_KHIEN + CAU_HINH)
    ghi("luong_lichsu.json", LICH_SU + CAU_HINH)
    ghi("luong_tong_hop.json", BANG_DIEU_KHIEN + LICH_SU + CAU_HINH)
