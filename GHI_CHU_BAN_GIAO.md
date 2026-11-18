# Ghi chú bàn giao – CanhBaoChay

Các ghi chú mà kế hoạch phân công yêu cầu từng task nộp kèm file, cùng kết quả kiểm thử đã chạy.

## Task 1 – Cách chia phòng và lý do

**Chọn:** 2 ESP32, mỗi con 10 phòng (esp01: 101–110, esp02: 111–120), cả 20 phòng đều là phòng thật có DHT22 riêng.

| Chức năng | Chân ESP32 | Ghi chú |
| --- | --- | --- |
| DHT22 phòng thứ 1…10 | GPIO 19, 16, 17, 21, 22, 25, 26, 27, 32, 33 | Thử trên Wokwi: DHT ở GPIO 4, 5, 13, 14 hay TIMEOUT nên tránh; tránh chân flash 6–11 và chân chỉ vào 34–39 |
| 74HC595 DATA / CLOCK / LATCH | GPIO 23 / 18 / 5 | 3 IC nối chuỗi = 24 ngõ ra, dùng 20 |
| Nút bật/tắt MQTT | GPIO 34 | Chân chỉ vào, điện trở 10k kéo xuống GND; bấm nối 3V3 (HIGH) |
| Còi chung | GPIO 2 | Phát tiếng bằng `tone()` khi có phòng báo động |

Bit trong chuỗi 595: phòng thứ i có đèn ở bit 2i, còi ở bit 2i+1 (IC1: phòng 1–4, IC2: phòng 5–8, IC3: phòng 9–10).

**Lý do:**

- Mỗi phòng cần 3 chân (cảm biến, đèn, còi); 10 phòng là 30 chân, nhiều hơn số GPIO dùng được của ESP32. Đẩy đèn và còi qua 74HC595 thì 10 phòng chỉ tốn 13 GPIO.
- Hai ESP32 thì làm được K10 (một thiết bị rớt, chỉ nhóm phòng của nó mất kết nối) và K17.
- Hai bản code chỉ khác dòng `#define SO_THIET_BI 1|2` (TB-09); `wokwi/tao_wokwi.py` sinh cả hai.
- Đọc cảm biến xoay vòng 200 ms một phòng, mỗi phòng vẫn đúng chu kỳ 2 s và thời gian chặn của DHT được rải đều.

**Về chân cảm biến:** bản đầu dùng GPIO 4, 13, 14 cho 3 phòng đầu; chạy trên Wokwi thì đúng 3 chân này hay báo TIMEOUT (đổi thứ tự phòng thì lỗi đi theo chân), GPIO 5 cũng vậy; bản cuối dùng 19, 21, 22 cho cảm biến và để GPIO 5 làm chân LATCH của 595 (chỉ xuất tín hiệu).

**Về còi:** theo tài liệu Wokwi, còi ở chế độ "smooth" hợp với tín hiệu `tone()`. Còi từng phòng nối qua 595 chỉ nhận mức HIGH/LOW, nên có thể không phát tiếng (hình còi vẫn hiển thị trên mạch). Vì vậy mạch có thêm **còi chung** trên GPIO 2 phát tiếng bằng `tone()` – đúng phương án dự phòng ở SRS mục 9.1. Đèn từng phòng là chỉ báo chính.

**Số phòng tối đa chạy mượt:** chưa đo được trên Wokwi (cần chạy thật). Cách đo: xem dòng `[giam sat] vong lap max … ms` in mỗi 10 s và thanh tốc độ mô phỏng của Wokwi; nếu dưới 100% thì chuyển một số phòng sang phòng ảo bằng lệnh `dat`.

## Task 1 – Cách mô phỏng lỗi cảm biến (K9)

Hai cách, dùng cách nào cũng được:

1. **Công tắc gạt trên dây DATA** của phòng thứ 3 và 4 mỗi thiết bị (103, 104 / 113, 114). Mặc định công tắc ở bên trái (nối dây). Gạt sang **phải** là đứt dây DATA, giống hỏng thật; ESP32 đọc ra NaN → `loi_cam_bien = true`, `nhiet_do = null`.
2. **Lệnh Serial** cho mọi phòng: `loi 105` để hỏng, `hetloi 105` để hết.

Quá 30 s vẫn lỗi thì đèn phòng đó nháy chậm (1 s/1 s) và còi bíp 100 ms mỗi 10 s (TB-10). Phòng đang báo động mà cảm biến hỏng thì vẫn giữ báo động (TB-05).

## Task 2 – Cách ngắt MQTT để demo (K7, K8)

- Bấm **nút xanh "MQTT on/off"** trên mạch Wokwi, hoặc gõ `mqtt off` / `mqtt on` ở Serial Monitor.
- Khi ngắt: đèn và còi tại phòng vẫn chạy (MQTT ở task FreeRTOS riêng); sau 15 s dashboard hiện MẤT KẾT NỐI cho 10 phòng của thiết bị đó.
- Khi nối lại: ESP32 gửi ngay trạng thái cả 10 phòng, dashboard cập nhật trong vài giây.
- Muốn mô phỏng ESP32 rớt hẳn (K10, K18): bấm Stop project Wokwi của thiết bị đó.

## Task 3 – Kết quả kiểm thử đã chạy

Kiểm thử chạy ngày 18/11/2026, ở hai mức:

- **Logic ESP32** (`kiemthu/test_logic.py`): biên dịch đúng đoạn logic trong `.ino` bằng g++ và chạy 27 kiểm tra – 27 đạt. Code cũng biên dịch không lỗi, không cảnh báo với ESP32 Arduino core 2.0.17 và 3.0.7.
- **Node-RED đầu-cuối**: broker MQTT cục bộ + Node-RED chạy `luong_tong_hop.json` + `gia_lap_esp32.js` bắn tin; đọc dashboard bằng trình duyệt headless và đọc thẳng file SQLite – 22 kiểm tra, 22 đạt.

Chưa chạy được ở đây: mạch Wokwi thật (cần tài khoản/trình duyệt), Telegram (cần token của nhóm). Cột cuối là việc nhóm còn phải làm.

| Mã | Tình huống | Kết quả đã chạy | Còn phải chạy trên Wokwi |
| --- | --- | --- | --- |
| K1 | Bình thường | Đạt – 20 ô đủ, tất cả BÌNH THƯỜNG | Đèn, còi tắt |
| K2 | Một phòng báo động | Đạt – logic bật ở lần đọc 47 °C thứ 2; dashboard BÁO ĐỘNG, phòng khác bình thường | Đèn, còi 102; đo độ trễ ≤ 4,5 s |
| K3 | Nhiều phòng | Đạt – 102 và 103 cùng báo, độc lập | Đèn nháy độc lập |
| K4 | Vùng giữa 42 °C | Đạt – vẫn BÁO ĐỘNG | – |
| K5 | Phục hồi | Đạt – 102 hết, 103 vẫn báo | – |
| K6 | Lịch sử | Đạt – 102: 1 đợt đã đóng, Tmax 47; 103: đang mở; bảng hiện "đang báo động"; biểu đồ có dữ liệu | – |
| K7 | Mất MQTT | Đạt phía dashboard – sau 15 s 101–110 MẤT KẾT NỐI | Đèn còi tại chỗ vẫn chạy khi bấm nút MQTT |
| K8 | Kết nối lại | Đạt – trở lại đúng trạng thái | Bấm nút MQTT lần nữa |
| K9 | Lỗi cảm biến | Đạt – LỖI CẢM BIẾN; phòng đang báo động giữ báo động, viền đỏ "còi đang kêu"; logic báo lỗi tại chỗ sau 30 s | Gạt công tắc 103/104; xem đèn nháy chậm |
| K10 | Một ESP32 rớt | Đạt – chỉ 101–110 MẤT KẾT NỐI | Stop project esp01 |
| K11 | Biên ngưỡng | Đạt (logic) – 44,9 không bật; 45,0 bật; 40,1 vẫn bật; 40,0 tắt | Lặp lại bằng `dat` |
| K12 | Khởi động lại Node-RED | Đạt – bảng còn đợt đang mở, sau đó đóng đúng, không tạo đợt trùng | – |
| K13 | Chạy 30 phút | Chưa chạy | Toàn bộ; ghi `vong lap max` và heap |
| K14 | Nhiễu một lần đọc | Đạt (logic) | Lệnh `nhieu 105 47` |
| K15 | Tăng nhanh | Đạt (logic) – 30 → 39 °C bật do tăng nhanh, giữ ≥ 60 s rồi tắt | Lệnh `dat 106 30`, `dat 106 39` |
| K16 | ESP32 treo | Đạt (logic: báo động lại trong 4 s; dashboard ghi "khởi động lại" khi `seq` lùi) | Lệnh `treo`, xem watchdog reset |
| K17 | Phòng chưa từng gửi tin | Đạt – 111–120 MẤT KẾT NỐI, "chưa nhận tin nào" | – |
| K18 | Mất kết nối khi đang báo động | Đạt – ô 103 viền đỏ "mất kết nối khi đang báo động"; đợt vẫn mở | Stop project esp01 khi 102 đang báo |
| K19 | Telegram | Chưa chạy | Điền token, chạy K2 |

Ảnh dashboard trong lúc kiểm thử nằm ở thư mục `anh_chup/`.

## v1.2 – Kết quả kiểm thử đã chạy (18/11/2026)

- **Logic ESP32** (`kiemthu/test_logic.py`): 53 kiểm tra, 53 đạt (27 của v1.1 và 26 mới cho K20–K24).
- **Biên dịch**: không lỗi trên ESP32 core 2.0.17 và 3.0.7, cả bản thường lẫn bản bật TLS. Firmware VS Code trong `wokwi/espXX/build/` đã dựng lại.
- **Node-RED đầu-cuối** (`kiemthu/e2e_v12.py`): broker cục bộ, giả lập 2 ESP32, Telegram giả lập (máy chủ HTTP đóng vai api.telegram.org), CSDL bắt đầu từ bản v1.1. 43 kiểm tra, 43 đạt.

| Mã | Tình huống | Kết quả | Còn phải chạy trên Wokwi / thật |
| --- | --- | --- | --- |
| K20 | Chú ý 38 °C | Đạt – 2 lần đọc ≥ 38 °C mới vào CHÚ Ý, ô vàng, không còi, không ngắt điện; ≤ 36 °C thì hết | Đèn sáng liên tục |
| K21 | Khói đơn thuần | Đạt – 2 lần đọc mới xác nhận; BÁO ĐỘNG 💨, không ngắt điện; Telegram có nút | Kéo thanh ppm của MQ-2 |
| K22 | Nguy hiểm | Đạt – ô đỏ thẫm nháy nhanh, 🔌, Telegram "NGUY HIỂM"; CSDL ghi muc_max 3, co_khoi, ngat_dien | Nghe còi liên tục, còi tầng |
| K23 | Ngắt điện chốt | Đạt – hết báo động vẫn 🔌; `capdien` (giữ nút 3 s) mới cấp lại, đang báo động thì không cho | Đèn vàng "điện phòng"; giữ nút thật |
| K24 | Tắt tiếng | Đạt – 🔕, hành lang ghi "còi chung đang tắt tiếng"; tự hết sau 300 s; phòng nặng thêm hoặc phòng khác mới báo thì huỷ | Bấm nút vàng, nghe còi tắt, đèn vẫn nháy |
| K25 | Giờ NTP | Trang Chi tiết hiện độ lệch giờ thiết bị, đã kiểm bằng giả lập | Chạy Wokwi, xem dòng "lệch … s" |
| K26 | Mặt bằng + chi tiết | Đạt – 2 tầng, 4 lối thoát; bấm 103 mở đúng trang chi tiết, nút ‹ › đổi phòng, "← Sơ đồ" quay lại | – |
| K27 | Telegram xác nhận | Đạt (Telegram giả lập) – tin được sửa "Đã xử lý: Lan (@lan_chu_tro)", CSDL ghi người và giờ; chat lạ bị từ chối; `/trangthai`, `/lichsu` đúng | Chạy với bot thật của nhóm |
| K28 | Leo thang | Đạt (Telegram giả lập) – 103 không ai bấm, sau 120 s gửi LEO THANG cho chat thứ hai; 105 đã xác nhận thì không | Chạy với bot thật |
| K29 | Broker riêng TLS | Chưa chạy – bản bật TLS biên dịch không lỗi | Tạo HiveMQ Cloud, điền tài khoản |
| K30 | Nhật ký trạng thái (MR-16) | Đạt – 102 ghi BÌNH THƯỜNG → CHÚ Ý → NGUY HIỂM, ngắt/cấp lại điện, tắt tiếng cả tầng, xác nhận Telegram; ngắt esp02 ghi 10 dòng → MẤT KẾT NỐI và 10 dòng nối lại; reset ghi 1 dòng khởi động lại; lọc phòng 102 đúng | – |
| – | Nâng cấp CSDL v1.1 | Đạt – thêm đủ 5 cột, dữ liệu cũ giữ nguyên | – |

Chưa chạy ở đây: mạch Wokwi v1.2 (MQ-2, 74HC165, rơ-le) chưa mở bằng simulator, vì cần license Wokwi trên máy nhóm. Logic đã kiểm, chân và dây đã kiểm tên linh kiện; lần đầu chạy nên gõ `trangthai` và kéo MQ-2 từng phòng để xác nhận đúng phòng (thứ tự đọc 74HC165 xem chú thích hàm `docKhoi()`). Broker TLS mới biên dịch, chưa kết nối HiveMQ Cloud thật.

## Những điểm đã quyết khi code (không có trong SRS)

- **Broker: `broker.emqx.io` thay cho `broker.hivemq.com`.** Chạy thật 2 ESP32 trên Wokwi (VS Code) ngày 18/11/2026: với hivemq, mỗi phòng mất 30–50% tin, dashboard liên tục báo MẤT KẾT NỐI; chuyển sang emqx thì 20/20 phòng BÌNH THƯỜNG suốt thời gian theo dõi, chỉ mất 1 tin lúc chuyển. Dự phòng: `test.mosquitto.org`.
- **Gửi định kỳ rải đều mỗi 0,5 s một phòng** (mỗi phòng vẫn 5 s/tin) thay vì dồn 10 tin cùng lúc.
- **Vòng lặp `delay(10)`** thay cho `delay(1)`: đủ cho nhịp đèn 250 ms, mô phỏng Wokwi nhanh hơn (đo được ~37% → ~73% tốc độ thật khi chạy 2 ESP32).
- **Lỗi cảm biến cũng cần 2 lần đọc hỏng liên tiếp** mới báo, để một lần DHT TIMEOUT lẻ tẻ không làm dashboard nhấp nháy.

- **Tăng nhanh cũng cần 2 lần đọc liên tiếp**, giống ngưỡng 45 °C. Nếu không, một lần đọc nhiễu 47 °C sẽ thỏa điều kiện "tăng ≥ 8 °C" và làm K14 thất bại.
- **`seq` chỉ tăng khi publish thành công**, nên lúc ngắt MQTT không bị tính là mất tin.
- **Node-RED nhận ra ESP32 khởi động lại khi `seq` nhỏ hơn lần trước**, và hiện dòng "Thiết bị khởi động lại" trong 10 phút.
- **Biểu đồ và bảng sự kiện vẽ bằng `ui-template`** thay vì `ui-chart`/`ui-table`, để tự vẽ đường ngưỡng 45/40 °C và không phụ thuộc cấu hình node biểu đồ.
- **SQL dùng tham số `$1, $2…`**: node `node-red-node-sqlite` chỉ gắn tham số khi số dấu `$` bằng số phần tử của `msg.payload`; dùng `?` thì giá trị không được gắn.
- **Telegram gọi thẳng API bằng node `http request`** có sẵn, không cần cài thêm gói.

### Thêm ở v1.2

- **Khói đơn thuần không ngắt điện**, chỉ báo động nhiệt hoặc NGUY HIỂM mới ngắt. Lý do: MQ-2 dễ báo nhầm khi nấu ăn, ngắt điện cả phòng vì khói bếp thì người ở sẽ tháo cảm biến.
- **Điện đã ngắt thì chốt**, kể cả khi hết báo động. Phải có người tới kiểm tra rồi giữ nút 3 s (hoặc lệnh `capdien`) mới cấp lại, và chỉ cấp được khi phòng đã dưới cấp BÁO ĐỘNG.
- **Rơ-le dùng kiểu pnp trong Wokwi** (IN thấp = COM nối NC = có điện), để khi ESP32 khởi động lại hoặc mất điều khiển thì phòng vẫn có điện, không ngắt nhầm.
- **Telegram dùng getUpdates mỗi 3 s** thay vì webhook, vì máy chạy Node-RED không có IP công khai.
- **Nút "Đã xử lý" mang mã `phòng|thời điểm bắt đầu đợt`**, nên bấm nút của một đợt cũ không xác nhận nhầm đợt mới.
- **Trang chi tiết dùng chung** cho mọi trình duyệt đang mở (lưu phòng đang xem trong `global`), đủ cho demo một người điều khiển.
- **Biến `TELEGRAM_API`** chỉ để kiểm thử với máy chủ giả; dùng thật thì để trống.
- **Nhật ký ghi theo trạng thái hiển thị** (6 trạng thái mục 4.4), tính ở Node-RED mỗi giây, nên mất kết nối cũng được ghi dù ESP32 không gửi được gì. Tắt tiếng và khởi động lại là của cả thiết bị nên ghi một dòng cho tầng, không ghi 10 dòng.
- **`cap_nhat_flow.js` chỉ thay các node có id `cbc_...`**, giữ biến Telegram và node broker đang chạy, nên đổi broker sang TLS trong editor rồi cập nhật flow cũng không mất.
