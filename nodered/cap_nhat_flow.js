#!/usr/bin/env node
/*
 * Cập nhật flow CanhBaoChay vào Node-RED đang chạy, không cần Import bằng tay.
 *
 *   node nodered/cap_nhat_flow.js            (Node-RED ở http://localhost:1880)
 *   node nodered/cap_nhat_flow.js --ep       (deploy lại kể cả khi flow không đổi)
 *   node nodered/cap_nhat_flow.js --cho 90   (Node-RED vừa bật: chờ tối đa 90 s cho nó lên)
 *
 * Việc script làm:
 *  1. Cài gói còn thiếu (@flowfuse/node-red-dashboard, node-red-node-sqlite) qua Admin API.
 *  2. Nếu flow trong file khác bản đang chạy: thay các node "cbc_..." bằng bản trong
 *     luong_tong_hop.json, GIỮ NGUYÊN các tab/node khác của bạn.
 *  3. Giữ biến môi trường Telegram đã điền ở tab LichSu và cấu hình broker đang dùng
 *     (nếu bạn đã đổi sang broker riêng/TLS thì không bị ghi đè).
 * Flow không đổi thì không làm gì, nên chay_he_thong.bat gọi script này mỗi lần khởi động.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const NODE_RED = process.env.NODE_RED_URL || 'http://localhost:1880';
const FILE = path.join(__dirname, 'luong_tong_hop.json');
const GOI_CAN = ['@flowfuse/node-red-dashboard', 'node-red-node-sqlite'];
const EP = process.argv.includes('--ep');
const iCho = process.argv.indexOf('--cho');
const CHO_S = iCho > 0 ? parseInt(process.argv[iCho + 1], 10) || 60 : 0;
const ngu = ms => new Promise(r => setTimeout(r, ms));

function goi(method, duongDan, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(duongDan, NODE_RED);
    const data = body === undefined ? null : Buffer.from(JSON.stringify(body), 'utf8');
    const req = http.request(u, {
      method,
      headers: Object.assign({ 'Node-RED-API-Version': 'v2', Accept: 'application/json' },
        data ? { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': data.length } : {}, headers),
      timeout: 300000,
    }, res => {
      const parts = [];
      res.on('data', c => parts.push(c));
      res.on('end', () => {
        const text = Buffer.concat(parts).toString('utf8');
        if (res.statusCode >= 400) return reject(new Error(`${method} ${duongDan}: HTTP ${res.statusCode} ${text.slice(0, 300)}`));
        try { resolve(text ? JSON.parse(text) : null); } catch { resolve(text); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('het thoi gian cho ' + duongDan)));
    if (data) req.write(data);
    req.end();
  });
}

const laCuaMinh = n => typeof n.id === 'string' && n.id.startsWith('cbc_');

async function main() {
  // 0. Node-RED có đang chạy không
  let dsGoi;
  const hetHan = Date.now() + CHO_S * 1000;
  for (;;) {
    try { dsGoi = await goi('GET', '/nodes'); break; }
    catch (e) { if (Date.now() >= hetHan) { dsGoi = e; break; } await ngu(2000); }
  }
  if (dsGoi instanceof Error) {
    const e = dsGoi;
    console.error('[cap nhat] Khong ket noi duoc Node-RED o ' + NODE_RED + ' (' + e.message + ').');
    console.error('           Hay chay Node-RED truoc (chay_he_thong.bat hoac lenh node-red).');
    process.exit(2);
  }

  // 1. Cài gói còn thiếu
  const daCo = new Set((dsGoi || []).map(n => n.module));
  let vuaCai = false;
  for (const g of GOI_CAN) {
    if (daCo.has(g)) continue;
    console.log(`[cap nhat] Dang cai ${g} (lan dau mat 1-3 phut)...`);
    await goi('POST', '/nodes', { module: g });
    console.log(`[cap nhat] Da cai ${g}`);
    vuaCai = true;
  }

  // 2. So phiên bản flow
  const noiDung = fs.readFileSync(FILE, 'utf8');
  const hash = crypto.createHash('sha1').update(noiDung).digest('hex').slice(0, 12);
  const moi = JSON.parse(noiDung);
  const hienTai = await goi('GET', '/flows');
  const flows = hienTai.flows || hienTai;
  const rev = hienTai.rev;
  const tabCu = flows.find(n => n.id === 'cbc_tab_bdk');
  if (!EP && !vuaCai && tabCu && tabCu.cbc_phien_ban === hash) {
    console.log(`[cap nhat] Flow da la ban moi nhat (${hash}), khong can deploy.`);
    return;
  }

  // 3. Giữ cấu hình người dùng đã sửa
  const cuTheoId = new Map(flows.filter(laCuaMinh).map(n => [n.id, n]));
  for (const n of moi) {
    if (n.id === 'cbc_tab_bdk') n.cbc_phien_ban = hash;
    const cu = cuTheoId.get(n.id);
    if (!cu) continue;
    if (n.id === 'cbc_tab_ls' && Array.isArray(cu.env)) {          // biến Telegram đã điền
      const giaTri = new Map(cu.env.map(e => [e.name, e]));
      n.env = n.env.map(e => (giaTri.has(e.name) && giaTri.get(e.name).value !== '') ? giaTri.get(e.name) : e);
    }
    if (n.type === 'mqtt-broker' || n.type === 'sqlitedb') {        // broker / CSDL đang dùng
      Object.assign(n, cu);
    }
  }
  const giuLai = flows.filter(n => !laCuaMinh(n));
  const ketQua = giuLai.concat(moi);

  await goi('POST', '/flows', { rev, flows: ketQua }, { 'Node-RED-Deployment-Type': 'full' });
  const coTg = (moi.find(n => n.id === 'cbc_tab_ls').env || []).some(e => e.name === 'TELEGRAM_TOKEN' && e.value);
  console.log(`[cap nhat] Da deploy flow CanhBaoChay ban ${hash}: ${moi.length} node` +
              (giuLai.length ? `, giu nguyen ${giuLai.length} node khac cua ban` : '') + '.');
  console.log('[cap nhat] Telegram: ' + (coTg ? 'da co token (giu nguyen).' : 'chua dien token (xem README muc Telegram).'));
}

main().catch(e => { console.error('[cap nhat] LOI: ' + e.message); process.exit(1); });
