# CanhBaoChay – hệ thống giám sát nhiệt độ và cảnh báo cháy phòng trọ

> **Mới tải project về?** Đọc [HUONG_DAN_CAI_DAT.md](HUONG_DAN_CAI_DAT.md): cài 3 phần mềm, clone, double-click `chay_he_thong.bat`.

Triển khai theo **SRS CanhBaoChay v1.2**. 20 phòng, 2 ESP32 mô phỏng trên Wokwi, MQTT (broker công cộng hoặc broker riêng có TLS), dashboard và lịch sử trên Node-RED.

**Có gì mới ở v1.2 (SRS mục 10):**
- Cảm biến khói MQ-2 mỗi phòng, đọc qua 2 IC 74HC165, và 3 cấp cảnh báo: CHÚ Ý (≥ 38 °C), BÁO ĐỘNG (≥ 45 °C hoặc có khói), NGUY HIỂM (khói kèm nhiệt cao).
- Rơ-le ngắt điện từng phòng khi báo động nhiệt hoặc NGUY HIỂM, chốt lại cho tới khi người kiểm tra xong giữ nút 3 s để cấp lại.
- Nút TẮT TIẾNG: bấm ngắn tắt còi 5 phút, đèn vẫn nháy. Tự huỷ nếu có phòng nặng thêm.
- Dashboard dạng sơ đồ mặt bằng 2 tầng, có lối thoát, cầu thang, bình chữa cháy. Bấm vào phòng mở trang Chi tiết phòng.
- Telegram hai chiều: nút "✅ Đã xử lý", sau 2 phút chưa ai bấm thì leo thang sang người thứ hai, lệnh `/trangthai`, `/lichsu`.
- Giờ NTP trong tin (`ts`). Broker riêng có TLS (ví dụ HiveMQ Cloud) chỉ cần điền tài khoản.
- Nhật ký trạng thái: mọi lần phòng đổi trạng thái, ngắt/cấp lại điện, tắt tiếng, thiết bị khởi động lại, xác nhận Telegram đều được ghi lại (giữ 90 ngày), lọc theo phòng/ngày/loại.

## Cài đặt và chạy (Windows)

**Cài một lần trên mỗi máy** (3 thứ, đều miễn phí):
1. **Node.js** bản LTS: https://nodejs.org
2. **VS Code**: https://code.visualstudio.com
3. **Git** (để clone và pull): https://git-scm.com

Node-RED, gói dashboard, SQLite, extension Wokwi và extension tự chạy mô phỏng **không cần cài tay**: file khởi động tự cài ở lần chạy đầu (mất vài phút).

**Lấy project về** (thư mục nào cũng được):
```powershell
git clone https://github.com/huydung2401/IOT_CanhBaoChay.git
```
Lần sau lấy bản mới: mở thư mục project, chạy `git pull`. Flow Node-RED mới được tự đưa vào ở lần khởi động kế tiếp.

**Mỗi lần chạy:** double-click `chay_he_thong.bat` trong thư mục project. File này:
1. kiểm tra Node.js, tự cài Node-RED nếu chưa có,
2. tự cài extension Wokwi và Auto Run Command cho VS Code,
3. bật Node-RED (thu nhỏ ở thanh tác vụ), tự cài gói còn thiếu và **tự đưa flow mới nhất vào Node-RED** (flow không đổi thì bỏ qua; giữ biến Telegram, cấu hình broker và các tab khác của bạn),
4. mở 2 cửa sổ VS Code chạy mô phỏng esp01, esp02 (firmware đã biên dịch sẵn trong `wokwi/espXX/build`, không cần cài Arduino),
5. mở dashboard `http://localhost:1880/dashboard` và xếp cửa sổ.

**Lần đầu trên máy mới:** VS Code báo **INVALID LICENSE** trong khung Wokwi → bấm **F1** → `Wokwi: Request a New License` → xác nhận trên trình duyệt (cần tài khoản Wokwi, miễn phí, 30 ngày xin lại một lần). Sau đó bấm nút ⟳ trong khung Wokwi.

Đừng thu nhỏ hay che kín hai cửa sổ VS Code: Wokwi sẽ chạy chậm và phòng bị báo MẤT KẾT NỐI. Đừng chạy bằng "Run as administrator". Bấm chuột vào khung Wokwi một lần để có tiếng còi.

**Hai máy cùng chạy một lúc:** mỗi ESP32 mô phỏng có client ID ngẫu nhiên nên không đá nhau khỏi broker, nhưng cùng tiền tố topic nên dashboard của hai máy sẽ nhận dữ liệu của nhau (phòng 101 nhảy qua lại giữa hai máy). Muốn chạy riêng: đổi dãy `73915` trong `TIEN_TO_TOPIC` ở cả 3 file `canhbaochay_esp32/canhbaochay_mqtt.h`, `nodered/tao_flow.py`, `kiemthu/gia_lap_esp32.js`, rồi chạy `python wokwi/tao_wokwi.py`, `python nodered/tao_flow.py` và biên dịch lại firmware (`wokwi/build_vscode.ps1`). Chỉ demo trên một máy thì không cần.

**Không đưa lên Git:** `canhbaochay.db` (dữ liệu chạy), `node_modules`, token Telegram (nằm trong Node-RED, không nằm trong file nào của project). Xem `.gitignore`.

Chỉ muốn cập nhật flow mà không mở mô phỏng: double-click `cap_nhat_node_red.bat`. Lưu ý: nếu bạn sửa tay node nào có id `cbc_...` trong editor Node-RED, lần cập nhật flow sau sẽ thay bằng bản trong file.

## Cấu trúc thư mục

| Đường dẫn | Nội dung | Task |
| --- | --- | --- |
| `canhbaochay_esp32/canhbaochay_esp32.ino` | Code ESP32: đọc nhiệt và khói, 3 cấp cảnh báo, đèn/còi/rơ-le, nút tắt tiếng, lệnh Serial, watchdog | 1 |
| `canhbaochay_esp32/canhbaochay_mqtt.h` | Wi-Fi, MQTT trong task FreeRTOS riêng, JSON có `seq`, `muc`, `ts`; NTP; TLS tuỳ chọn | 2 |
| `wokwi/esp01/`, `wokwi/esp02/` | Hai project Wokwi dựng sẵn (code + `diagram.json` + `libraries.txt`) | 1 |
| `wokwi/tao_wokwi.py` | Sinh lại hai project Wokwi từ code gốc | 1 |
| `nodered/luong_bangdieukhien.json` | Tab BangDieuKhien: sơ đồ mặt bằng 20 phòng, 6 trạng thái, mất kết nối | 2 |
| `nodered/luong_lichsu.json` | Tab LichSu: SQLite, biểu đồ, bảng sự kiện, trang Chi tiết phòng, Telegram hai chiều | 3 |
| `nodered/luong_tong_hop.json` | Cả hai tab, import một lần khi đã ghép | 3 |
| `nodered/tao_flow.py` | Sinh lại ba file flow | 2, 3 |
| `nodered/cap_nhat_flow.js` | Đưa flow vào Node-RED đang chạy qua Admin API (tự cài gói thiếu, giữ cấu hình của bạn) | 2, 3 |
| `chay_he_thong.bat`, `cap_nhat_node_red.bat` | Bấm một lần để chạy cả hệ thống / chỉ cập nhật flow | – |
| `kiemthu/test_logic.py` | Kiểm thử logic báo động trên máy tính (53 kiểm tra) | 1 |
| `kiemthu/e2e_v12.py` | Kiểm thử đầu-cuối Node-RED v1.2 với broker cục bộ và Telegram giả lập (43 kiểm tra) | 2, 3 |
| `kiemthu/gia_lap_esp32.js` | Giả lập 2 ESP32 gửi MQTT, để làm dashboard khi chưa có Wokwi | 2, 3 |
| `GHI_CHU_BAN_GIAO.md` | Cách chia phòng, mô phỏng lỗi, ngắt MQTT, kết quả kiểm thử | 1, 2, 3 |
| `anh_chup/` | Ảnh dashboard lúc chạy kiểm thử, dùng cho báo cáo | 3 |

## Việc phải làm trước tiên: đổi tiền tố topic

Broker công cộng dùng chung với mọi người, nên nhóm đổi dãy số `73915` thành dãy riêng ở **3 chỗ**, giống hệt nhau:

1. `canhbaochay_esp32/canhbaochay_mqtt.h` – hằng `TIEN_TO_TOPIC` và tiền tố client ID.
2. `nodered/tao_flow.py` – hằng `TIEN_TO_TOPIC`, rồi chạy `python3 nodered/tao_flow.py`.
3. `kiemthu/gia_lap_esp32.js` – hằng `TIEN_TO_TOPIC`.

Sau đó chạy `python3 wokwi/tao_wokwi.py` để chép code mới sang hai project Wokwi.

## Chạy phần ESP32 trên Wokwi

1. Vào wokwi.com, tạo project **ESP32** mới (mỗi ESP32 một project, mở trong hai tab trình duyệt).
2. Với project esp01: thay nội dung `sketch.ino` bằng `wokwi/esp01/canhbaochay_esp32.ino`, thêm file `canhbaochay_mqtt.h`, `libraries.txt`, và thay `diagram.json` bằng file cùng tên trong `wokwi/esp01/`.
3. Làm tương tự cho esp02 với thư mục `wokwi/esp02/`.
4. Bấm Start. Serial Monitor in `[wifi] da ket noi` rồi `[mqtt] da ket noi`.
5. Bấm vào cảm biến DHT22 để chỉnh nhiệt độ; bấm vào cảm biến khói (MQ-2) kéo thanh ppm lên cao để giả lập có khói; gõ lệnh ở Serial Monitor (bảng bên dưới).

Cảm biến khói cần **20 s làm nóng** sau khi bật, trong thời gian này chỉ lệnh `khoi` có tác dụng. Hết 20 s, Serial in `[khoi] cam bien khoi san sang`; nếu cả 10 phòng cùng báo khói ngay lúc đó, máy coi là lỗi dây/IC 74HC165, in `[khoi] LOI ...` và tạm bỏ qua khói (báo động nhiệt vẫn chạy).

Mạch mỗi ESP32 (v1.2): 10 DHT22, 10 MQ-2 → 2 × 74HC165 (PL = D4, CP = D13, Q7 = D35), 4 × 74HC595 (đèn, còi, rơ-le), 10 rơ-le kèm đèn vàng "điện phòng" (sáng = có điện), nút TẮT TIẾNG ở D15, nút MQTT ở D34, còi hành lang ở D2.

Hai bản code trong `wokwi/esp01` và `wokwi/esp02` chỉ khác nhau một dòng `#define SO_THIET_BI`. Sửa code thì sửa ở `canhbaochay_esp32/` rồi chạy lại `tao_wokwi.py`, không sửa tay hai bản sao.

Muốn nạp ESP32 thật bằng Arduino IDE: mở `canhbaochay_esp32/canhbaochay_esp32.ino`, cài thư viện **PubSubClient** và **DHT sensor library for ESPx**, chọn board ESP32 Dev Module. Ngoài Wokwi thì sửa `WIFI_SSID`, `WIFI_MAT_KHAU` trong `canhbaochay_mqtt.h`.

## Chạy bằng extension Wokwi trong VS Code

Mỗi thư mục `wokwi/esp01`, `wokwi/esp02` có sẵn `wokwi.toml` và firmware đã biên dịch trong `build/`.

1. Lấy license miễn phí: **F1** → `Wokwi: Request a New License` → đăng nhập trên trình duyệt → bấm mở lại VS Code. License hết hạn sau 30 ngày thì xin lại.
2. **File → Open Folder** → chọn `<thư mục project>\wokwi\esp01` (mở đúng thư mục con, để `wokwi.toml` nằm ở gốc).
3. **F1** → `Wokwi: Start Simulator`. Muốn mở cả esp02: **File → New Window**, mở `<thư mục project>\wokwi\esp02`, rồi Start Simulator ở cửa sổ đó.
4. Sửa code ở `canhbaochay_esp32/` thì phải biên dịch lại firmware: `powershell -ExecutionPolicy Bypass -File wokwi\build_vscode.ps1` (hướng dẫn cài arduino-cli ở đầu file script).

### Lệnh Serial (SRS mục 7.3)

| Lệnh | Tác dụng | Dùng cho |
| --- | --- | --- |
| `dat 105 47` | Ép nhiệt độ phòng 105 là 47 °C | Phòng ảo, K11, K15 |
| `tha 105` | Phòng 105 đọc lại cảm biến | K11 |
| `nhieu 105 47` | Chỉ lần đọc kế tiếp là 47 °C | K14 |
| `loi 105` / `hetloi 105` | Giả lập cảm biến hỏng / hết hỏng | K9 |
| `khoi 105` / `hetkhoi 105` | Ép có khói / bỏ ép (không cần kéo thanh MQ-2) | K21, K22 |
| `tattieng` | Như bấm nút TẮT TIẾNG (tắt còi 5 phút) | K23, K24 |
| `capdien 105` / `capdien all` | Như giữ nút 3 s: cấp lại điện phòng đã hết báo động | K22 |
| `khoiraw` | In 16 bit thô đọc từ 74HC165 và phòng nào đang có khói (bật/tắt in mỗi khi đổi) | Chẩn đoán MQ-2 |
| `mqtt off` / `mqtt on` | Ngắt / nối lại MQTT (hoặc bấm nút xanh trên mạch) | K7, K8 |
| `treo` | Cố ý treo vòng lặp để watchdog khởi động lại | K16 |
| `trangthai` | In bảng phòng, trạng thái MQTT | Kiểm tra nhanh |

## Chạy phần Node-RED

1. Cài Node-RED (Node.js 18 trở lên): `npm install -g --unsafe-perm node-red`, rồi chạy `node-red`.
2. Mở `http://localhost:1880`, menu ☰ → **Manage palette** → **Install**: cài `@flowfuse/node-red-dashboard` và `node-red-node-sqlite`.
3. Menu ☰ → **Import** → chọn file:
   - Đã ghép: `nodered/luong_tong_hop.json`.
   - Từng người làm riêng: import file tab của mình. Nếu import file thứ hai, Node-RED báo trùng node cấu hình (broker, ui-base, ui-theme) → chọn **bỏ qua/không import bản sao** các node đó.
4. Bấm **Deploy**. Mở dashboard ở `http://localhost:1880/dashboard`.
5. File SQLite `canhbaochay.db` được tạo trong thư mục chạy lệnh `node-red`. CSDL tạo từ bản v1.1 được tự thêm cột mới khi khởi động, dữ liệu cũ giữ nguyên.

**Nâng cấp từ v1.1:** xoá hai tab BangDieuKhien và LichSu cũ (chọn tab → menu ☰ → Flows → Delete), rồi Import lại `luong_tong_hop.json` → Deploy. Nhớ điền lại biến Telegram nếu đã dùng.

Trang dashboard: **Bảng điều khiển** (sơ đồ mặt bằng), **Lịch sử** (biểu đồ, bảng đợt báo động, nhật ký trạng thái có lọc), **Chi tiết phòng** (mở khi bấm vào một phòng, có 20 dòng nhật ký gần nhất của phòng). Trang chi tiết dùng chung cho mọi trình duyệt đang mở: ai bấm phòng nào thì trang chi tiết hiện phòng đó.

### Telegram hai chiều (DB-10, MR-13, MR-14)

1. Mở Telegram, nhắn `@BotFather` → `/newbot` → đặt tên → nhận **token**.
2. Tạo nhóm "Nhà trọ 01", thêm bot vào nhóm, gửi một tin bất kỳ trong nhóm. Mở `https://api.telegram.org/bot<TOKEN>/getUpdates` trên trình duyệt, tìm `"chat":{"id":-100...}` → đó là **chat_id** (số âm với nhóm).
3. (Tuỳ chọn) Người thứ hai để leo thang (ví dụ chủ trọ): người đó nhắn `/start` cho bot, lấy `chat_id` cá nhân cũng bằng getUpdates.
4. Double-click tab **LichSu** → **Environment variables**: điền `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, và `TELEGRAM_CHAT_ID_2` nếu có → Deploy. `TELEGRAM_API` để trống.
5. Thử: gõ `/trangthai` trong nhóm, bot trả lời tình trạng 20 phòng. Khi có báo động, tin có nút **✅ Đã xử lý**; bấm thì tin được sửa thành "Đã xử lý: tên, giờ" và bảng Lịch sử ghi người xác nhận. Không ai bấm sau 2 phút thì bot gửi tin LEO THANG cho người thứ hai (hoặc nhắc lại trong nhóm).
6. Chỉ chat có trong biến môi trường mới bấm nút và gõ lệnh được. Để trống token thì flow không gửi gì. **Không đưa token vào file nộp hoặc GitHub.**

Bot dùng `getUpdates` hỏi Telegram mỗi 3 s nên chạy được trên máy cá nhân, không cần IP công khai. Không đặt webhook cho bot này, vì có webhook thì getUpdates không nhận được tin.

### Broker riêng có TLS (MR-08, tuỳ chọn)

Mặc định dùng `broker.emqx.io` không mã hoá để chạy ngay. Muốn dữ liệu không bị người lạ đọc:

1. Đăng ký HiveMQ Cloud bản miễn phí (Serverless) → tạo cluster → **Access Management** tạo tài khoản, ví dụ `canhbaochay` / mật khẩu mạnh. Ghi lại địa chỉ cluster dạng `xxxxxxxx.s1.eu.hivemq.cloud`.
2. `canhbaochay_esp32/canhbaochay_mqtt.h`: điền `MQTT_TEN_DANG_NHAP`, `MQTT_MAT_KHAU`, `MQTT_MAY_CHU_RIENG`. Có tên đăng nhập thì code tự chuyển sang TLS cổng 8883 (chứng chỉ ISRG Root X1 đã nhúng sẵn). Chạy lại `tao_wokwi.py` và biên dịch lại firmware.
3. Node-RED: double-click node broker **Broker CanhBaoChay** → Server = địa chỉ cluster, Port 8883, tick **Use TLS** → tab **Security** điền tài khoản → Deploy.
4. Giả lập: `node gia_lap_esp32.js mqtts://canhbaochay:MATKHAU@xxxxxxxx.s1.eu.hivemq.cloud:8883`.

Serial in `[mqtt] that bai, ma loi 4/5` là sai tài khoản; `-2` là không tới được máy chủ hoặc TLS hỏng.

## Chạy khi chưa có Wokwi

```bash
cd kiemthu
npm install mqtt
node gia_lap_esp32.js                         # gửi lên broker.emqx.io
node gia_lap_esp32.js mqtt://localhost:1883   # hoặc broker cục bộ
```

Gõ `dat 102 47`, `dat 104 39`, `khoi 105`, `tattieng esp01`, `capdien all`, `loi 104`, `dung esp01`, `chay esp01`, `reset esp02`… để tạo các tình huống trên dashboard.

## Kiểm thử logic trên máy tính

```bash
python3 kiemthu/test_logic.py      # cần g++
```

Script trích nguyên văn đoạn logic báo động từ file `.ino`, nên kết quả phản ánh đúng code nạp lên ESP32.

Kiểm thử đầu-cuối Node-RED (cần Node-RED, aedes, mqtt, playwright cài trong một thư mục, xem đầu file): `python3 kiemthu/e2e_v12.py`.
