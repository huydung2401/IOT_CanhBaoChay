# Hướng dẫn cài đặt và chạy CanhBaoChay

Hệ thống giám sát nhiệt độ và cảnh báo cháy cho nhà trọ 20 phòng: 2 ESP32 mô phỏng trên Wokwi, gửi dữ liệu qua MQTT, hiển thị và lưu lịch sử trên Node-RED.

Làm theo thứ tự dưới đây là chạy được, không cần cài Arduino, không cần biên dịch.

---

## 1. Cài 3 phần mềm (một lần, miễn phí)

| Phần mềm | Tải ở | Ghi chú |
| --- | --- | --- |
| **Node.js** bản LTS | https://nodejs.org | Cài mặc định, bấm Next đến hết |
| **VS Code** | https://code.visualstudio.com | Cài mặc định |
| **Git** | https://git-scm.com | Cài mặc định |

Kiểm tra: mở **PowerShell** gõ `node -v` và `git --version`, thấy số phiên bản là được.

Ngoài ra cần một **tài khoản Wokwi** (miễn phí, đăng ký bằng Google/GitHub tại https://wokwi.com) để lấy license chạy mô phỏng trong VS Code.

> Không cần cài tay: Node-RED, gói dashboard, SQLite, extension Wokwi, extension tự chạy mô phỏng. File khởi động tự cài ở lần chạy đầu.

---

## 2. Tải project về

Mở PowerShell, vào thư mục muốn để project (ví dụ `D:\`), chạy:

```powershell
cd D:\
git clone https://github.com/huydung2401/IOT_CanhBaoChay.git
```

Lệnh tạo thư mục `D:\IOT_CanhBaoChay`. Nếu repo để riêng tư (Private), chủ repo phải mời bạn làm Collaborator trước; lần đầu clone Git sẽ mở trình duyệt để bạn đăng nhập GitHub.

Đặt ở thư mục nào cũng được, nên tránh đường dẫn có dấu ngoặc `( )`.

---

## 3. Chạy lần đầu

1. Vào thư mục `IOT_CanhBaoChay`, **double-click `chay_he_thong.bat`**. Không chọn "Run as administrator".
2. Lần đầu mất **3–5 phút**: cửa sổ đen sẽ cài Node-RED, gói dashboard, SQLite và extension VS Code. Đừng tắt nó.
3. Hai cửa sổ VS Code mở ra (esp01, esp02). Khung Wokwi báo **INVALID LICENSE** là bình thường ở lần đầu:
   - Bấm vào cửa sổ VS Code → nhấn **F1** → gõ `Wokwi: Request a New License` → Enter.
   - Trình duyệt mở trang Wokwi → đăng nhập → bấm xác nhận gửi license về VS Code (có thể phải xác nhận 2 lần).
   - VS Code báo "License activated" → bấm nút **⟳** màu xanh trong khung Wokwi. Làm ở cả hai cửa sổ.
   - License có hạn **30 ngày**, hết hạn làm lại bước này.
4. Trình duyệt mở dashboard `http://localhost:1880/dashboard`. Đợi **30–60 giây**, 20 phòng chuyển **BÌNH THƯỜNG** (xanh).

Lần sau chỉ cần double-click `chay_he_thong.bat`, khoảng 30 giây là lên.

### Để hệ thống chạy ổn định

- **Không thu nhỏ, không che kín hai cửa sổ VS Code.** Wokwi bị ẩn sẽ chạy chậm, dashboard báo MẤT KẾT NỐI. File khởi động đã tự xếp: dashboard bên trái, hai mô phỏng bên phải.
- **Không đóng cửa sổ Node-RED** (đang thu nhỏ dưới thanh tác vụ).
- Muốn nghe còi: **bấm chuột vào khung Wokwi một lần** (trình duyệt trong VS Code chỉ phát tiếng sau khi có thao tác).

---

## 4. Dùng thử

### Dashboard

| Trang | Có gì |
| --- | --- |
| **Bảng điều khiển** | Sơ đồ mặt bằng 2 tầng, 20 phòng, 6 trạng thái màu. Bấm vào một phòng để xem chi tiết |
| **Lịch sử** | Biểu đồ nhiệt 30 phút, bảng các đợt báo động, nhật ký mọi lần đổi trạng thái (lọc theo phòng, ngày, loại) |
| **Chi tiết phòng** | Trạng thái, khói, điện, còi, biểu đồ, các đợt báo động và nhật ký của riêng phòng đó |

Ý nghĩa màu: xanh **BÌNH THƯỜNG** · vàng **CHÚ Ý** (≥ 38 °C) · đỏ nháy **BÁO ĐỘNG** (≥ 45 °C hoặc có khói) · đỏ thẫm nháy nhanh **NGUY HIỂM** (khói + nhiệt cao) · tím **LỖI CẢM BIẾN** · xám **MẤT KẾT NỐI**. Biểu tượng: 💨 khói, 🔌 đã ngắt điện, 🔕 đang tắt tiếng.

### Tạo tình huống trên mạch Wokwi

- **Nóng lên:** bấm vào cảm biến nhiệt DHT22 của một phòng, kéo nhiệt độ lên 39 °C (CHÚ Ý) hoặc 47 °C (BÁO ĐỘNG, ngắt điện phòng).
- **Có khói:** bấm vào cảm biến khói MQ-2 (hàng trên cùng), kéo **ppm** lên gần tối đa. Cảm biến khói cần **20 giây làm nóng** sau khi bật, trước đó không báo khói.
- **Nút vàng TẮT TIẾNG:** bấm ngắn = tắt còi 5 phút (đèn vẫn nháy); giữ 3 giây = cấp lại điện các phòng đã hết báo động.
- **Nút xanh dương:** ngắt / nối lại MQTT, để thử MẤT KẾT NỐI.
- **Công tắc gạt** ở 2 phòng: giả lập cảm biến nhiệt hỏng.

### Lệnh gõ trong Serial Monitor (terminal phía dưới khung Wokwi)

| Lệnh | Tác dụng |
| --- | --- |
| `dat 102 47` / `tha 102` | Ép nhiệt phòng 102 = 47 °C / bỏ ép |
| `khoi 105` / `hetkhoi 105` | Ép có khói phòng 105 / bỏ ép |
| `loi 104` / `hetloi 104` | Giả lập cảm biến nhiệt hỏng / hết hỏng |
| `tattieng` | Như bấm nút tắt tiếng |
| `capdien all` | Như giữ nút 3 giây: cấp lại điện |
| `mqtt off` / `mqtt on` | Ngắt / nối lại MQTT |
| `trangthai` | In trạng thái 10 phòng |
| `khoiraw` | In tín hiệu thô của cảm biến khói (chẩn đoán) |

Kịch bản demo nhanh: `dat 102 39` (CHÚ Ý) → `khoi 102` (NGUY HIỂM, ngắt điện, còi hú) → bấm nút tắt tiếng → `hetkhoi 102`, `dat 102 30` (hết báo động, điện vẫn ngắt) → giữ nút 3 giây (cấp lại điện) → mở trang Lịch sử xem nhật ký.

---

## 5. Telegram (tuỳ chọn)

Mỗi máy tự cài bot của mình, token **không** nằm trong repo.

1. Telegram → nhắn `@BotFather` → `/newbot` → đặt tên → nhận **token**.
2. Tạo nhóm, thêm bot vào nhóm, gửi một tin bất kỳ. Mở `https://api.telegram.org/bot<TOKEN>/getUpdates`, tìm `"chat":{"id":-100...}` → đó là **chat_id**.
3. Mở `http://localhost:1880` → double-click tab **LichSu** → **Environment variables** → điền `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (tuỳ chọn `TELEGRAM_CHAT_ID_2` cho người nhận leo thang) → **Done** → **Deploy**.
4. Gõ `/trangthai` trong nhóm để thử. Khi báo động, tin có nút **✅ Đã xử lý**; sau 2 phút chưa ai bấm thì bot gửi cho người thứ hai.

Cập nhật project bằng `git pull` không làm mất các biến này.

---

## 6. Lấy bản mới

```powershell
cd D:\IOT_CanhBaoChay
git pull
```

Rồi chạy lại `chay_he_thong.bat`. Flow Node-RED mới tự được đưa vào; Telegram, broker và các tab bạn tự thêm được giữ nguyên.

Nếu `git pull` báo xung đột vì bạn đã sửa file, cách đơn giản nhất (bỏ hết thay đổi của bạn trong project): `git reset --hard` rồi `git pull`.

---

## 7. Gặp lỗi

| Hiện tượng | Cách xử lý |
| --- | --- |
| Cửa sổ đen báo **Chưa cài Node.js** / **Không tìm thấy VS Code** | Cài theo mục 1 rồi chạy lại |
| **INVALID LICENSE** trong khung Wokwi | Làm bước 3.3 (F1 → Wokwi: Request a New License) |
| Khung Wokwi không tự chạy | Trong cửa sổ VS Code đó nhấn **F1** → `Wokwi: Start Simulator` |
| Dashboard trắng / không mở được | Đợi thêm 30 giây rồi tải lại trang. Vẫn không được: mở cửa sổ Node-RED dưới thanh tác vụ xem lỗi |
| Nhiều phòng **MẤT KẾT NỐI** rồi tự hết | Cửa sổ VS Code bị thu nhỏ/che. Để hai cửa sổ hiện, xem % tốc độ góc phải khung Wokwi nên trên 50% |
| Tất cả phòng **MẤT KẾT NỐI** | Mạng chặn broker `broker.emqx.io` cổng 1883 (mạng trường, công ty). Thử Wi-Fi điện thoại |
| Cả 20 phòng báo khói ngay khi chạy | Bấm ⟳ hai khung Wokwi. Serial in `[khoi] LOI ...` thì gõ `khoiraw`, chụp gửi nhóm |
| Không nghe còi | Bấm chuột vào khung Wokwi một lần; kiểm tra loa máy |
| VS Code ghi **[Administrator]** trên thanh tiêu đề, mô phỏng không mở | Đóng hết VS Code, chạy lại `chay_he_thong.bat` bằng double-click thường |
| Cửa sổ đen báo cổng **1880** đang dùng | Đã có Node-RED khác chạy. Đóng nó (hoặc khởi động lại máy) rồi chạy lại |
| Thông báo Ionide / .NET hoặc extension lạ trong VS Code | Không liên quan, bấm X bỏ qua |

### Hai máy cùng chạy một lúc

Các máy clone từ cùng repo dùng chung broker và chung topic. Nếu hai người **cùng bật mô phỏng một lúc**, dashboard mỗi máy sẽ nhận dữ liệu của cả hai (phòng nhảy qua lại). Khi demo chỉ để **một máy** chạy mô phỏng. Muốn tách hẳn, xem mục "Hai máy cùng chạy một lúc" trong `README.md`.

---

## 8. Cấu trúc thư mục (để tham khảo)

| Thư mục / file | Nội dung |
| --- | --- |
| `chay_he_thong.bat` | **Bấm cái này để chạy tất cả** |
| `cap_nhat_node_red.bat` | Chỉ cập nhật flow Node-RED |
| `canhbaochay_esp32/` | Mã nguồn ESP32 |
| `wokwi/esp01`, `wokwi/esp02` | Mạch mô phỏng + firmware đã biên dịch |
| `nodered/` | Flow Node-RED và script tự cập nhật |
| `kiemthu/` | Kiểm thử logic, giả lập ESP32 bằng Node.js, kiểm thử đầu-cuối |
| `anh_chup/` | Ảnh giao diện |
| `README.md` | Tài liệu kỹ thuật đầy đủ (broker riêng TLS, biên dịch lại, chi tiết từng yêu cầu) |
| `GHI_CHU_BAN_GIAO.md` | Kết quả kiểm thử và các quyết định khi code |

Chạy không cần Wokwi (chỉ để thử dashboard): mở PowerShell trong thư mục `kiemthu`, chạy `npm install` một lần, rồi `node gia_lap_esp32.js` để giả lập 2 ESP32; gõ `dat 102 47`, `khoi 105`… ngay trong cửa sổ đó.
