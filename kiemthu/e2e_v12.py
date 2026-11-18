import json, subprocess, time, sqlite3, os, shutil, pathlib, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

NR = pathlib.Path('/home/claude/nrtest'); P = pathlib.Path('/home/claude/project')
UD = NR / 'ud12'

# ---------------- Telegram giả (mock) ----------------
TG = {'goi': [], 'cho': [], 'id': 0, 'msg': 100}
class TgHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _tra(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200)
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); method = u.path.rsplit('/', 1)[-1]
        if method == 'getUpdates':
            off = int(parse_qs(u.query).get('offset', ['0'])[0])
            TG['cho'] = [x for x in TG['cho'] if x['update_id'] >= off]
            return self._tra({'ok': True, 'result': TG['cho']})
        self._tra({'ok': False})
    def do_POST(self):
        method = self.path.rsplit('/', 1)[-1]
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        TG['goi'].append((method, body))
        if method == 'sendMessage':
            TG['msg'] += 1
            return self._tra({'ok': True, 'result': {'message_id': TG['msg'], 'chat': {'id': body.get('chat_id')}, 'text': body.get('text')}})
        self._tra({'ok': True, 'result': True})
def tg_update(**kw):
    TG['id'] += 1; kw['update_id'] = TG['id']; TG['cho'].append(kw)
def tg_tim(method, chua='', chat=None):
    return [b for m, b in TG['goi'] if m == method and chua in json.dumps(b, ensure_ascii=False)
            and (chat is None or str(b.get('chat_id')) == chat)]
srv = ThreadingHTTPServer(('127.0.0.1', 8999), TgHandler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

# ---------------- chuẩn bị ----------------
def prep():
    if UD.exists(): shutil.rmtree(UD)
    UD.mkdir()
    flows = json.loads((P / 'nodered/luong_tong_hop.json').read_text())
    for n in flows:
        if n['type'] == 'mqtt-broker': n['broker'] = 'localhost'
        if n['id'] == 'cbc_tab_ls':
            for e in n['env']:
                e['value'] = {'TELEGRAM_TOKEN': 'TEST', 'TELEGRAM_CHAT_ID': '111', 'TELEGRAM_CHAT_ID_2': '222',
                              'TELEGRAM_API': 'http://127.0.0.1:8999'}[e['name']]
    (UD / 'flows.json').write_text(json.dumps(flows))
    # CSDL bản v1.1 (thiếu cột) để kiểm tra nâng cấp tự động
    con = sqlite3.connect(UD / 'canhbaochay.db')
    con.execute('CREATE TABLE su_kien (id INTEGER PRIMARY KEY AUTOINCREMENT, ma_phong TEXT NOT NULL, bat_dau INTEGER NOT NULL, ket_thuc INTEGER, nhiet_do_max REAL)')
    con.execute("INSERT INTO su_kien (ma_phong, bat_dau, ket_thuc, nhiet_do_max) VALUES ('119', 1700000000000, 1700000300000, 46.5)")
    con.commit(); con.close()

def start_nr():
    open(NR / 'nr12.log', 'w').close()
    log = open(NR / 'nr12.log', 'a')
    p = subprocess.Popen(['node', str(NR / 'node_modules/node-red/red.js'), '-u', str(UD), '-p', '1880', 'flows.json'],
                         cwd=UD, stdout=log, stderr=log)
    for _ in range(60):
        time.sleep(1)
        if 'Started flows' in (NR / 'nr12.log').read_text(): break
    return p
def wait(s, why=''): print(f'  ... cho {s}s {why}', flush=True); time.sleep(s)
def cmd(c): print('  >', c, flush=True); sim.stdin.write(c + '\n'); sim.stdin.flush()
fails = 0
def check(cond, desc):
    global fails
    print(('  DAT   ' if cond else '  KHONG ') + desc, flush=True)
    if not cond: fails += 1
def so_do(page, mo=True):
    if mo: page.goto('http://localhost:1880/dashboard/bangdieukhien')
    page.wait_for_selector('.phong', timeout=15000); time.sleep(1.5)
    out = {}
    for el in page.query_selector_all('.phong'):
        ma = el.query_selector('.dau b').inner_text().strip()
        out[ma] = {'text': ' | '.join(x.strip() for x in el.inner_text().split('\n') if x.strip()),
                   'cls': el.get_attribute('class')}
    return out
def st(c, ma): return c[ma]['text']
def db(q):
    con = sqlite3.connect(UD / 'canhbaochay.db'); r = con.execute(q).fetchall(); con.close(); return r

prep()
broker = subprocess.Popen(['node', 'broker.js'], cwd=NR); time.sleep(1)
nr = start_nr()
env = dict(os.environ, NODE_PATH=str(NR / 'node_modules'))
sim = subprocess.Popen(['node', str(P / 'kiemthu/gia_lap_esp32.js'), 'mqtt://localhost:1883'], stdin=subprocess.PIPE,
                       text=True, env=env, stdout=open(NR / 'sim12.log', 'w'), stderr=subprocess.STDOUT)
try:
  with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_page(viewport={'width': 1366, 'height': 1000})
    print('Nang cap CSDL v1.1 -> v1.2'); wait(6)
    cot = [r[1] for r in db('PRAGMA table_info(su_kien)')]
    check(all(c in cot for c in ['muc_max', 'co_khoi', 'ngat_dien', 'xac_nhan_boi', 'xac_nhan_luc']), 'them du 5 cot moi: ' + ','.join(cot))
    check(db("SELECT count(*) FROM su_kien WHERE ma_phong='119'")[0][0] == 1, 'giu nguyen du lieu cu')

    print('MR-10 so do mat bang')
    c = so_do(page)
    check(len(c) == 20, f'so do co {len(c)} phong')
    body = page.inner_text('body')
    check(body.count('LỐI THOÁT') == 4 and 'Tầng 1' in body and 'Tầng 2' in body, '2 tang, 4 loi thoat')
    check(all('BÌNH THƯỜNG' in v['text'] for v in c.values()), 'tat ca BINH THUONG')

    print('K20 CHU Y'); cmd('dat 102 39'); wait(6)
    c = so_do(page); check('CHÚ Ý' in st(c, '102') and 'cy' in c['102']['cls'], '102 CHU Y: ' + st(c, '102'))
    check('🔌' not in st(c, '102'), 'CHU Y khong ngat dien')

    print('K21 khoi don thuan'); cmd('khoi 105'); wait(5)
    c = so_do(page); check('BÁO ĐỘNG' in st(c, '105') and '💨' in st(c, '105') and '🔌' not in st(c, '105'), '105 BAO DONG + khoi, khong ngat: ' + st(c, '105'))
    m105 = tg_tim('sendMessage', 'BÁO ĐỘNG phòng 105')
    check(len(m105) == 1 and 'reply_markup' in m105[0], 'Telegram bao dong 105 co nut Da xu ly')

    print('K22 NGUY HIEM'); cmd('khoi 102'); wait(5)
    c = so_do(page); check('NGUY HIỂM' in st(c, '102') and 'nh' in c['102']['cls'] and '🔌' in st(c, '102'), '102 NGUY HIEM + ngat dien: ' + st(c, '102'))
    check(len(tg_tim('sendMessage', 'NGUY HIỂM phòng 102')) == 1, 'Telegram NGUY HIEM 102')

    print('Bao dong nhiet'); cmd('dat 103 47'); wait(6)
    t103 = time.time()
    c = so_do(page); check('BÁO ĐỘNG' in st(c, '103') and '🔌' in st(c, '103'), '103 BAO DONG + ngat dien: ' + st(c, '103'))
    page.screenshot(path=str(NR / 'v12_sodo.png'), full_page=True)

    print('K23 tat tieng'); cmd('tattieng esp01'); wait(4)
    c = so_do(page); check('🔕' in st(c, '103') and 'tắt tiếng' in page.inner_text('body'), '103 hien tat tieng, hanh lang ghi tat tieng')

    print('MR-11 chi tiet phong')
    page.click('.phong:has-text("103")'); page.wait_for_url('**/chitiet', timeout=10000); time.sleep(4)
    txt = page.inner_text('body')
    check('Phòng 103' in txt and 'ĐÃ NGẮT' in txt and 'BÁO ĐỘNG' in txt, 'trang chi tiet 103: trang thai + ngat dien')
    check('esp01' in txt and 'đang báo động' in txt, 'chi tiet co thiet bi va dot dang mo')
    check('Nhật ký trạng thái' in txt and 'BÌNH THƯỜNG → BÁO ĐỘNG' in txt and 'rơ-le ngắt điện phòng' in txt and 'cả tầng esp01' in txt,
          'chi tiet co nhat ky: BT -> BAO DONG, ngat dien, tat tieng ca tang')
    page.screenshot(path=str(NR / 'v12_chitiet.png'), full_page=True)
    page.click('button:has-text("›")'); time.sleep(4)
    check('Phòng 104' in page.inner_text('body'), 'nut › chuyen sang phong 104')
    page.click('button:has-text("Sơ đồ")'); page.wait_for_url('**/bangdieukhien', timeout=10000)
    check(True, 'nut Quay lai ve so do')

    print('MR-13 xac nhan qua Telegram')
    cb = m105[0]['reply_markup']['inline_keyboard'][0][0]['callback_data']
    msg105 = {'message_id': 101, 'chat': {'id': 111}, 'text': m105[0]['text']}
    tg_update(callback_query={'id': 'q1', 'from': {'first_name': 'Lan', 'username': 'lan_chu_tro'}, 'message': msg105, 'data': cb})
    tg_update(callback_query={'id': 'q2', 'from': {'first_name': 'La'}, 'message': {'message_id': 9, 'chat': {'id': 999}, 'text': 'x'}, 'data': cb})
    tg_update(message={'message_id': 50, 'chat': {'id': 111}, 'text': '/trangthai'})
    tg_update(message={'message_id': 51, 'chat': {'id': 111}, 'text': '/lichsu@canhbaochay_bot'})
    wait(7)
    check(any(b['callback_query_id'] == 'q1' and 'ghi nhận' in b['text'] for b in tg_tim('answerCallbackQuery')), 'tra loi bam nut')
    check(len(tg_tim('editMessageText', 'Đã xử lý: Lan (@lan_chu_tro)')) == 1, 'sua tin goc: da xu ly boi Lan')
    check(any(b['callback_query_id'] == 'q2' and 'không có quyền' in b['text'] for b in tg_tim('answerCallbackQuery')), 'chat la khong duoc xac nhan')
    r = db("SELECT xac_nhan_boi FROM su_kien WHERE ma_phong='105'")
    check(r and r[0][0] and 'Lan' in r[0][0], f'CSDL ghi nguoi xac nhan: {r}')
    st_msg = tg_tim('sendMessage', 'Trạng thái lúc', chat='111')
    check(st_msg and '102: NGUY HIỂM' in st_msg[-1]['text'], '/trangthai liet ke 102 NGUY HIEM')
    check(len(tg_tim('sendMessage', '5 đợt báo động gần nhất')) == 1, '/lichsu tra 5 dot')

    print('MR-14 leo thang (103 chua xac nhan)')
    con_lai = 135 - (time.time() - t103)
    if con_lai > 0: wait(int(con_lai), 'cho qua 120 s')
    lt = tg_tim('sendMessage', 'LEO THANG', chat='222')
    check(any('phòng 103' in x['text'] for x in lt), 'leo thang 103 sang nguoi thu hai')
    check(not any('phòng 105' in x['text'] for x in lt), '105 da xac nhan: khong leo thang')

    print('MR-04/05 cap lai dien'); cmd('hetkhoi 102'); cmd('hetkhoi 105'); cmd('dat 103 30'); cmd('dat 102 30'); wait(6)
    c = so_do(page)
    check('BÌNH THƯỜNG' in st(c, '103') and '🔌' in st(c, '103'), '103 het bao dong nhung dien van ngat: ' + st(c, '103'))
    check(len(tg_tim('sendMessage', 'Phòng 103 hết báo động')) == 1, 'Telegram het bao dong 103')
    cmd('capdien all'); wait(4)
    c = so_do(page); check('🔌' not in st(c, '103') and '🔌' not in st(c, '102'), 'giu nut: cap lai dien 102, 103')

    print('MR-16 nhat ky trang thai')
    nk = db("SELECT ma_phong, ma_thiet_bi, loai, tu, den FROM nhat_ky ORDER BY id")
    for r in nk: print('   ', r)
    def co(*dong): return any(all(x is None or x == y for x, y in zip(dong, r)) for r in nk)
    check(co('102', 'esp01', 'trang_thai', 'BÌNH THƯỜNG', 'CHÚ Ý') and co('102', 'esp01', 'trang_thai', 'CHÚ Ý', 'NGUY HIỂM'), '102: BT -> CHU Y -> NGUY HIEM')
    check(co('102', 'esp01', 'dien', 'có điện', 'ngắt') and co('103', 'esp01', 'dien', 'ngắt', 'có điện'), 'ghi ngat dien va cap lai dien')
    check(co(None, 'esp01', 'tat_tieng', 'còi bật', 'tắt tiếng'), 'ghi tat tieng ca tang esp01')
    check(co('105', None, 'xac_nhan'), 'ghi xac nhan Telegram 105')
    check(co('103', 'esp01', 'trang_thai', 'BÁO ĐỘNG', 'BÌNH THƯỜNG'), '103: BAO DONG -> BINH THUONG')
    check(sum(1 for r in nk if r[2] == 'dien' and r[0] == '105') == 0, 'khoi don thuan 105 khong ghi ngat dien')
    cmd('dung esp02'); wait(18, 'esp02 mat ket noi')
    cmd('chay esp02'); wait(5); cmd('reset esp02'); wait(5)
    nk = db("SELECT ma_phong, ma_thiet_bi, loai, tu, den FROM nhat_ky ORDER BY id")
    check(sum(1 for r in nk if r[4] == 'MẤT KẾT NỐI' and r[1] == 'esp02') == 10, '10 phong esp02 ghi -> MAT KET NOI')
    check(sum(1 for r in nk if r[3] == 'MẤT KẾT NỐI' and r[1] == 'esp02') == 10, '10 phong esp02 ghi MAT KET NOI -> ...')
    check(sum(1 for r in nk if r[2] == 'khoi_dong_lai' and r[1] == 'esp02') == 1, 'esp02 khoi dong lai: ghi 1 dong')
    page.goto('http://localhost:1880/dashboard/lichsu'); time.sleep(5)
    txt = page.inner_text('body')
    check('Nhật ký trạng thái' in txt and 'CHÚ Ý → NGUY HIỂM' in txt and 'Khởi động lại' in txt, 'trang Lich su co khung nhat ky')
    page.locator('.nk select').first.select_option('102'); time.sleep(6)
    rows = page.locator('.nk tbody tr').all_inner_texts()
    check(rows and all('102' in r for r in rows), f'loc phong 102: {len(rows)} dong, deu la 102')
    page.locator('.nk select').first.select_option(''); time.sleep(1)

    print('LS-03 bang su kien')
    page.goto('http://localhost:1880/dashboard/lichsu'); time.sleep(4)
    txt = page.inner_text('body')
    check('NGUY HIỂM' in txt and 'Lan' in txt and '💨' in txt, 'bang su kien co cap, khoi, nguoi xac nhan')
    page.screenshot(path=str(NR / 'v12_lichsu.png'), full_page=True)
    rows = db('SELECT ma_phong, muc_max, co_khoi, ngat_dien, ket_thuc IS NOT NULL FROM su_kien ORDER BY id')
    print('   ', rows)
    check(('102', 3, 1, 1, 1) in rows and ('105', 2, 1, 0, 1) in rows and ('103', 2, 0, 1, 1) in rows, 'CSDL ghi dung cap/khoi/ngat dien')

    page2 = b.new_page(viewport={'width': 390, 'height': 844}); so_do(page2)
    page2.screenshot(path=str(NR / 'v12_mobile.png'), full_page=True)
    b.close()
finally:
    for p_ in (sim, nr, broker): p_.terminate()
    srv.shutdown()
print('\nKHONG DAT:', fails)
errs = [l for l in (NR / 'nr12.log').read_text().splitlines() if 'error' in l.lower() or '[warn]' in l.lower()]
print('\n'.join(errs[:25]))
