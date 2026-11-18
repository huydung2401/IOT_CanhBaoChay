/*
 * CanhBaoChay - Thiết bị đầu cuối ESP32 (Task 1)
 * Đặc tả: SRS CanhBaoChay v1.2, yêu cầu TB-01 .. TB-12, MR-01 .. MR-07
 *
 * Mỗi ESP32 phụ trách 10 phòng của một tầng:
 *   - 10 cảm biến nhiệt DHT22 nối thẳng GPIO (Wokwi không có DHT11)
 *   - 10 cảm biến khói MQ-2, chân DOUT đọc qua 2 IC 74HC165 (GPIO 4/13/14)   [MR-01]
 *   - 10 đèn + 10 còi + 10 rơ-le ngắt điện qua 4 IC 74HC595 (GPIO 23/18/5)    [MR-04]
 *   - Còi hành lang của tầng trên GPIO 2, phát tiếng bằng tone()              [MR-06]
 *   - Nút GPIO 34 (kéo xuống 10k, bấm = HIGH): bật/tắt MQTT để demo K7, K8
 *   - Nút GPIO 15 (INPUT_PULLUP): bấm = tắt tiếng 5 phút, giữ 3 s = cấp lại điện [MR-05]
 *   - Không dùng GPIO 4, 5, 12, 13, 14, 15 cho DHT: thử trên Wokwi, DHT ở các chân này
 *     hay báo TIMEOUT (các chân đó chỉ dùng cho tín hiệu số đơn giản)
 *
 * Ba cấp cảnh báo (MR-02): 1 CHÚ Ý, 2 BÁO ĐỘNG, 3 NGUY HIỂM. Phần MQTT nằm trong
 * canhbaochay_mqtt.h (Task 2), chạy ở task FreeRTOS riêng nên mất mạng không làm
 * đứng đèn, còi (TB-07, NF-04).
 *
 * Đổi thiết bị: chỉ sửa SO_THIET_BI bên dưới (TB-09).
 */

#include <DHTesp.h>
#include <esp_task_wdt.h>
#include <esp_arduino_version.h>

// ======================= CHỌN THIẾT BỊ (TB-09) =======================
#ifndef SO_THIET_BI
#define SO_THIET_BI 2   // 1 = esp01 (tầng 1, phòng 101-110), 2 = esp02 (tầng 2, phòng 111-120)
#endif            // build cho VS Code truyền -DSO_THIET_BI=2 (wokwi/build_vscode.ps1)

// ======================= CẤU HÌNH CHUNG (bảng thống nhất 1.3) ==========
const float    NGUONG_BAT_C            = 45.0;
const float    NGUONG_TAT_C            = 40.0;
const uint32_t CHU_KY_DOC_MS           = 2000;
const uint32_t CHU_KY_GUI_MS           = 5000;
const uint32_t CHU_KY_NOI_LAI_MS       = 5000;
const uint16_t THOI_GIAN_MAT_KET_NOI_S = 15;   // dùng ở Node-RED, ghi để đồng bộ

// ======================= BỔ SUNG BẢN 1.1 ================================
const uint8_t  SO_LAN_XAC_NHAN = 2;     // TB-03: số lần đọc liên tiếp để bật; cũng dùng để xác nhận lỗi, khói
const uint16_t THOI_GIAN_LOI_S = 30;    // TB-10: lỗi bao lâu thì báo tại chỗ
const float    TOC_DO_TANG_C   = 8.0;   // TB-11: tăng bao nhiêu độ ...
const uint16_t CUA_SO_TANG_S   = 60;    // TB-11: ... trong bao nhiêu giây
const uint8_t  WDT_TIMEOUT_S   = 5;     // TB-12

// ======================= BỔ SUNG BẢN 1.2 ================================
const float    NGUONG_CHU_Y_C       = 38.0;   // MR-02: cấp 1 CHÚ Ý
const float    NGUONG_HET_CHU_Y_C   = 36.0;
const uint32_t CHU_KY_DOC_KHOI_MS   = 500;    // MR-01: đọc 10 MQ-2 mỗi 0,5 s
const uint32_t THOI_GIAN_LAM_NONG_MS = 20000;  // MQ-2 cần làm nóng: 20 s đầu bỏ qua kết quả đọc
const uint16_t THOI_GIAN_TAT_TIENG_S = 300;   // MR-05
const uint16_t THOI_GIAN_GIU_CAP_DIEN_MS = 3000;  // MR-05: giữ nút 3 s để cấp lại điện

// ======================= RIÊNG TỪNG THIẾT BỊ ===========================
#if SO_THIET_BI == 1
const char* MA_THIET_BI = "esp01";
const char* DS_PHONG[]  = {"101","102","103","104","105","106","107","108","109","110"};
#elif SO_THIET_BI == 2
const char* MA_THIET_BI = "esp02";
const char* DS_PHONG[]  = {"111","112","113","114","115","116","117","118","119","120"};
#else
#error "SO_THIET_BI phai la 1 hoac 2"
#endif

#define SO_PHONG 10
static_assert(sizeof(DS_PHONG) / sizeof(DS_PHONG[0]) == SO_PHONG, "DS_PHONG phai co dung 10 phong");

// ======================= CHÂN (mục 7.1, 10.3) ===========================
const uint8_t CHAN_DHT[SO_PHONG] = {19, 16, 17, 21, 22, 25, 26, 27, 32, 33};
const uint8_t CHAN_595_DATA  = 23;
const uint8_t CHAN_595_CLOCK = 18;
const uint8_t CHAN_595_LATCH = 5;    // chỉ xuất tín hiệu, không cần chân "đẹp"
const uint8_t CHAN_165_PL    = 4;    // 74HC165: nạp song song (tích cực mức thấp)
const uint8_t CHAN_165_CP    = 13;   // 74HC165: xung dịch
const uint8_t CHAN_165_Q7    = 35;   // 74HC165: dữ liệu ra (vào ESP32). GPIO35 chỉ vào (GPIO14 trên Wokwi nghi đọc sai)
const uint8_t CHAN_NUT_MQTT  = 34;   // chân chỉ vào, cần điện trở kéo xuống ngoài; bấm = HIGH
const uint8_t CHAN_NUT_TAT_TIENG = 15;  // INPUT_PULLUP, bấm = LOW
const uint8_t CHAN_COI_CHUNG = 2;
const uint16_t TAN_SO_COI    = 2000;   // Hz

// ======================= DỮ LIỆU DÙNG CHUNG VỚI PHẦN MQTT ===============
// Phần MQTT chỉ ĐỌC các mảng này (trong khóa), không ghi.
float nhietDo[SO_PHONG];      // NAN khi lỗi -> JSON null
bool  loiCamBien[SO_PHONG];
bool  baoDong[SO_PHONG];      // báo động NHIỆT (TB-03, TB-11). JSON bao_dong = muc >= 2
bool  khoi[SO_PHONG];         // MR-01: khói đã xác nhận
bool  chuY[SO_PHONG];         // MR-02: T >= 38 °C
bool  ngatDien[SO_PHONG];     // MR-04: rơ-le đang ngắt điện phòng (chốt)

portMUX_TYPE khoaDuLieu = portMUX_INITIALIZER_UNLOCKED;
#define KHOA()    portENTER_CRITICAL(&khoaDuLieu)
#define MO_KHOA() portEXIT_CRITICAL(&khoaDuLieu)

// === BAT DAU LOGIC BAO DONG (kiemthu/test_logic.py trích đoạn này) ===
// Chỉ dùng C++ thuần + KHOA()/MO_KHOA() để kiểm thử được trên máy tính.

#define SO_MAU (CUA_SO_TANG_S * 1000UL / CHU_KY_DOC_MS)   // 30 mẫu = 60 s

uint8_t  demVuot[SO_PHONG];        // số lần đọc liên tiếp >= NGUONG_BAT_C
uint8_t  demTang[SO_PHONG];        // số lần đọc liên tiếp thỏa điều kiện tăng nhanh
uint8_t  demLoi[SO_PHONG];         // số lần đọc hỏng liên tiếp
uint8_t  demChuY[SO_PHONG];        // số lần đọc liên tiếp >= NGUONG_CHU_Y_C
uint8_t  demKhoi[SO_PHONG];        // số lần đọc MQ-2 liên tiếp CÓ khói
uint8_t  demHetKhoi[SO_PHONG];     // số lần đọc MQ-2 liên tiếp KHÔNG khói
uint32_t loiTu[SO_PHONG];          // millis() lúc bắt đầu lỗi (TB-10)
bool     baoDongDoTang[SO_PHONG];  // đợt báo động hiện tại do tăng nhanh mà bật
uint32_t batDauBaoDong[SO_PHONG];  // millis() lúc bật báo động

float    mauT[SO_PHONG][SO_MAU];   // bộ đệm vòng các lần đọc hợp lệ (TB-11)
uint32_t mauMs[SO_PHONG][SO_MAU];
uint8_t  mauDau[SO_PHONG];
uint8_t  mauSo[SO_PHONG];

uint32_t tatTiengDen = 0;          // MR-05: millis() hết hạn tắt tiếng (0 = không tắt)
uint8_t  mucLucTatTieng[SO_PHONG]; // cấp của từng phòng lúc bấm tắt tiếng

void khoiTaoLogic() {
  for (uint8_t i = 0; i < SO_PHONG; i++) {
    nhietDo[i] = NAN; loiCamBien[i] = false; baoDong[i] = false;
    khoi[i] = false; chuY[i] = false; ngatDien[i] = false;
    demVuot[i] = 0; demTang[i] = 0; demLoi[i] = 0; demChuY[i] = 0;
    demKhoi[i] = 0; demHetKhoi[i] = 0; loiTu[i] = 0;
    baoDongDoTang[i] = false; batDauBaoDong[i] = 0;
    mauDau[i] = 0; mauSo[i] = 0; mucLucTatTieng[i] = 0;
  }
  tatTiengDen = 0;
}

// MR-02: cấp cảnh báo của phòng i. Gọi trong KHOA() hoặc khi không có task khác ghi.
uint8_t mucPhong(uint8_t i) {
  if (khoi[i] && (chuY[i] || baoDong[i])) return 3;   // NGUY HIỂM
  if (baoDong[i] || khoi[i])              return 2;   // BÁO ĐỘNG
  if (chuY[i])                            return 1;   // CHÚ Ý
  return 0;
}

// MR-04: ngắt điện khi báo động nhiệt hoặc cấp 3; khói đơn thuần không ngắt. Chốt lại.
void capNhatNgatDien(uint8_t i) {
  if (baoDong[i] || mucPhong(i) == 3) ngatDien[i] = true;
}

// MR-05: cấp lại điện, chỉ khi phòng đã hết báo động (cấp < 2). Trả về true nếu cấp lại.
bool capLaiDien(uint8_t i) {
  if (!ngatDien[i] || mucPhong(i) >= 2) return false;
  ngatDien[i] = false;
  return true;
}

void ghiMau(uint8_t i, float t, uint32_t now) {
  mauT[i][mauDau[i]] = t;
  mauMs[i][mauDau[i]] = now;
  mauDau[i] = (mauDau[i] + 1) % SO_MAU;
  if (mauSo[i] < SO_MAU) mauSo[i]++;
}

// TB-11: t cao hơn mức thấp nhất trong CUA_SO_TANG_S giây qua ít nhất TOC_DO_TANG_C
bool tangNhanh(uint8_t i, float t, uint32_t now) {
  bool coMau = false;
  float thapNhat = 0;
  for (uint8_t k = 0; k < mauSo[i]; k++) {
    if (now - mauMs[i][k] > CUA_SO_TANG_S * 1000UL) continue;
    if (!coMau || mauT[i][k] < thapNhat) { thapNhat = mauT[i][k]; coMau = true; }
  }
  return coMau && (t - thapNhat >= TOC_DO_TANG_C);
}

// Báo động do tăng nhanh phải giữ ít nhất CUA_SO_TANG_S giây rồi mới xét tắt
bool duThoiGianGiu(uint8_t i, uint32_t now) {
  return !baoDongDoTang[i] || (now - batDauBaoDong[i] >= CUA_SO_TANG_S * 1000UL);
}

// Gọi sau mỗi lần đọc nhiệt của phòng i. t = NAN nghĩa là đọc lỗi.
void capNhatBaoDong(uint8_t i, float t, uint32_t now) {
  if (isnan(t) || t < -40 || t > 80) {                 // TB-02 (dải DHT22)
    // Một lần đọc hỏng lẻ tẻ (DHT TIMEOUT khi mô phỏng chậm) thì bỏ qua, giữ nguyên mọi
    // trạng thái; hỏng SO_LAN_XAC_NHAN lần liên tiếp mới coi là lỗi cảm biến.
    if (demLoi[i] < 255) demLoi[i]++;
    if (demLoi[i] < SO_LAN_XAC_NHAN) return;
    KHOA();
    if (!loiCamBien[i]) loiTu[i] = now;
    loiCamBien[i] = true;
    nhietDo[i] = NAN;
    MO_KHOA();
    demVuot[i] = 0;
    demTang[i] = 0;
    demChuY[i] = 0;
    return;                                             // TB-05: baoDong, chuY giữ nguyên
  }

  demLoi[i] = 0;
  demVuot[i] = (t >= NGUONG_BAT_C) ? (uint8_t)min(demVuot[i] + 1, 255) : 0;
  demTang[i] = tangNhanh(i, t, now) ? (uint8_t)min(demTang[i] + 1, 255) : 0;
  demChuY[i] = (t >= NGUONG_CHU_Y_C) ? (uint8_t)min(demChuY[i] + 1, 255) : 0;
  ghiMau(i, t, now);

  KHOA();
  loiCamBien[i] = false;
  nhietDo[i] = t;
  if (!baoDong[i]) {
    bool doNguong = demVuot[i] >= SO_LAN_XAC_NHAN;   // TB-03
    bool doTang   = demTang[i] >= SO_LAN_XAC_NHAN;   // TB-11 (cũng xác nhận 2 lần)
    if (doNguong || doTang) {
      baoDong[i] = true;
      baoDongDoTang[i] = !doNguong;
      batDauBaoDong[i] = now;
    }
  } else if (t <= NGUONG_TAT_C && duThoiGianGiu(i, now)) { // TB-04
    baoDong[i] = false;
    baoDongDoTang[i] = false;
  }
  if (!chuY[i] && demChuY[i] >= SO_LAN_XAC_NHAN) chuY[i] = true;   // MR-02
  else if (chuY[i] && t <= NGUONG_HET_CHU_Y_C) chuY[i] = false;
  capNhatNgatDien(i);
  MO_KHOA();
}

// MR-01: gọi mỗi CHU_KY_DOC_KHOI_MS với kết quả đọc MQ-2 của phòng i
void capNhatKhoi(uint8_t i, bool coKhoi) {
  if (coKhoi) { demKhoi[i] = (uint8_t)min(demKhoi[i] + 1, 255); demHetKhoi[i] = 0; }
  else        { demHetKhoi[i] = (uint8_t)min(demHetKhoi[i] + 1, 255); demKhoi[i] = 0; }
  KHOA();
  if (!khoi[i] && demKhoi[i] >= SO_LAN_XAC_NHAN) khoi[i] = true;
  else if (khoi[i] && demHetKhoi[i] >= SO_LAN_XAC_NHAN) khoi[i] = false;
  capNhatNgatDien(i);
  MO_KHOA();
}

// MR-05: bấm tắt tiếng. Ghi nhớ cấp từng phòng để biết khi nào có phòng "nặng hơn".
void batTatTieng(uint32_t now) {
  KHOA();
  for (uint8_t i = 0; i < SO_PHONG; i++) mucLucTatTieng[i] = mucPhong(i);
  MO_KHOA();
  tatTiengDen = now + THOI_GIAN_TAT_TIENG_S * 1000UL;
  if (tatTiengDen == 0) tatTiengDen = 1;
}

// Đang tắt tiếng? Tự hủy khi hết hạn hoặc có phòng lên cấp cao hơn lúc bấm.
bool dangTatTieng(uint32_t now) {
  if (tatTiengDen == 0) return false;
  if ((int32_t)(now - tatTiengDen) >= 0) { tatTiengDen = 0; return false; }
  for (uint8_t i = 0; i < SO_PHONG; i++) {
    if (mucPhong(i) > mucLucTatTieng[i]) { tatTiengDen = 0; return false; }
  }
  return true;
}

// TB-10: lỗi liên tục quá THOI_GIAN_LOI_S giây
bool loiLau(uint8_t i, uint32_t now) {
  return loiCamBien[i] && (now - loiTu[i] >= THOI_GIAN_LOI_S * 1000UL);
}
// === KET THUC LOGIC BAO DONG ===

volatile bool tatTiengHienTai = false;   // phần MQTT đọc để gửi tat_tieng

#include "canhbaochay_mqtt.h"   // Task 2: dùng các mảng và khóa ở trên

// ======================= CẢM BIẾN VÀ LỆNH DEMO ==========================
DHTesp dht[SO_PHONG];
float giaTriEp[SO_PHONG];     // lệnh "dat": ép nhiệt độ (phòng ảo, K11, K15, K20)
float nhieuMotLan[SO_PHONG];  // lệnh "nhieu": chỉ một lần đọc (K14)
bool  epLoi[SO_PHONG];        // lệnh "loi": giả lập cảm biến hỏng (K9)
bool  epKhoi[SO_PHONG];       // lệnh "khoi": giả lập có khói (K21, K22)

uint8_t  phongKeTiep = 0;
uint32_t lanDocCuoi = 0;
uint32_t lanDocKhoi = 0;
// DHT22 cần tối thiểu 2 s giữa hai lần đọc. Đọc đúng 2000 ms thì sát giới hạn,
// cảm biến có lúc không trả lời (lỗi TIMEOUT giả). Dư 5 ms mỗi lượt -> mỗi phòng 2,05 s.
const uint32_t KHOANG_DOC_MS = CHU_KY_DOC_MS / SO_PHONG + 5;
const char* loiDht[SO_PHONG];   // mã lỗi lần đọc gần nhất, để in ra khi báo LOI CAM BIEN
uint8_t  mucTruoc[SO_PHONG];
bool     loiTruoc[SO_PHONG];
bool     ngatTruoc[SO_PHONG];

const char* TEN_MUC[] = {"BINH THUONG", "CHU Y", "BAO DONG", "NGUY HIEM"};

void inThayDoi(uint8_t i, uint32_t now) {
  KHOA();
  uint8_t m = mucPhong(i); bool l = loiCamBien[i]; bool n = ngatDien[i];
  float t = nhietDo[i]; bool k = khoi[i]; bool tang = baoDongDoTang[i];
  MO_KHOA();
  if (m != mucTruoc[i]) {
    Serial.printf("[%lu ms] Phong %s: %s (%.1f C%s%s)\r\n", (unsigned long)now, DS_PHONG[i],
                  TEN_MUC[m], t, k ? ", co khoi" : "", (m >= 2 && tang) ? ", tang nhanh" : "");
    mucTruoc[i] = m;
  }
  if (l != loiTruoc[i]) {
    if (l) Serial.printf("[%lu ms] Phong %s: LOI CAM BIEN (%s)\r\n", (unsigned long)now, DS_PHONG[i], loiDht[i]);
    else   Serial.printf("[%lu ms] Phong %s: cam bien doc lai duoc\r\n", (unsigned long)now, DS_PHONG[i]);
    loiTruoc[i] = l;
  }
  if (n != ngatTruoc[i]) {
    Serial.printf("[%lu ms] Phong %s: %s\r\n", (unsigned long)now, DS_PHONG[i],
                  n ? "NGAT DIEN (ro-le)" : "da cap lai dien");
    ngatTruoc[i] = n;
  }
}

void docMotPhong(uint8_t i) {
  float t;
  if (epLoi[i]) {
    t = NAN;
  } else if (!isnan(nhieuMotLan[i])) {
    t = nhieuMotLan[i];
    nhieuMotLan[i] = NAN;
  } else if (!isnan(giaTriEp[i])) {
    t = giaTriEp[i];
  } else {
    t = dht[i].getTemperature();
    if (dht[i].getStatus() != DHTesp::ERROR_NONE) { loiDht[i] = dht[i].getStatusString(); t = NAN; }
  }
  if (epLoi[i]) loiDht[i] = "gia lap bang lenh";
  uint32_t now = millis();
  capNhatBaoDong(i, t, now);
  inThayDoi(i, now);
}

// MR-01: đọc 16 bit từ chuỗi 2 IC 74HC165. IC2 (phòng 9, 10) nối ra ESP32 nên ra trước.
// Bit đọc thứ k: k < 8 -> IC2 chân D(7-k); k >= 8 -> IC1 chân D(15-k).
uint16_t khoiThoCuoi = 0;      // 16 bit thô lần đọc gần nhất (1 = chân mức cao = không khói)
bool     inKhoiTho   = false;  // lệnh "khoiraw": in 16 bit thô mỗi lần đọc
bool     loiDuongKhoi = false; // tự kiểm tra: cả 10 đầu vào cùng báo khói ngay khi khởi động

uint16_t doc165() {
  digitalWrite(CHAN_165_PL, LOW);       // chụp trạng thái 16 chân
  delayMicroseconds(5);
  digitalWrite(CHAN_165_PL, HIGH);
  delayMicroseconds(2);
  uint16_t tho = 0;
  for (uint8_t k = 0; k < 16; k++) {
    if (digitalRead(CHAN_165_Q7) == HIGH) tho |= (1u << k);
    digitalWrite(CHAN_165_CP, HIGH);
    delayMicroseconds(2);
    digitalWrite(CHAN_165_CP, LOW);
    delayMicroseconds(2);
  }
  return tho;
}

int phongCuaBit(uint8_t k) { return (k < 8) ? (8 + (7 - k)) : (15 - k); }   // IC2 D0,D1 = phòng thứ 9, 10

void inKhoi(uint16_t tho) {
  Serial.printf("[khoi] tho=0x%04X  phong co khoi:", tho);
  bool co = false;
  for (uint8_t k = 0; k < 16; k++) {
    int i = phongCuaBit(k);
    if (i >= 0 && i < SO_PHONG && !(tho & (1u << k))) { Serial.printf(" %s", DS_PHONG[i]); co = true; }
  }
  Serial.print(co ? "\r\n" : " (khong)\r\n");
}

void docKhoi() {
  uint16_t tho = doc165();
  if (inKhoiTho && tho != khoiThoCuoi) inKhoi(tho);
  khoiThoCuoi = tho;
  bool coKhoi[SO_PHONG] = {false};
  uint8_t soCo = 0;
  for (uint8_t k = 0; k < 16; k++) {
    int i = phongCuaBit(k);
    if (i >= 0 && i < SO_PHONG && !(tho & (1u << k))) { coKhoi[i] = true; soCo++; }   // DOUT LOW = có khói
  }
  uint32_t now = millis();
  static bool daLamNong = false;
  if (!daLamNong) {
    if (now < THOI_GIAN_LAM_NONG_MS) {           // MQ-2 đang làm nóng: chỉ nhận lệnh "khoi" giả lập
      for (uint8_t i = 0; i < SO_PHONG; i++) coKhoi[i] = false;
      soCo = 0;
    } else {
      daLamNong = true;
      inKhoi(tho);
      if (soCo == SO_PHONG) {                    // tự kiểm tra: 10/10 phòng cùng có khói lúc khởi động
        loiDuongKhoi = true;                     // = đứt dây / mất nguồn chuỗi 74HC165, không phải cháy
        Serial.println("[khoi] LOI: ca 10 dau vao deu bao khoi khi khoi dong -> nghi dut day/mat nguon 74HC165. "
                       "Tam bo qua cam bien khoi (bao dong nhiet van chay). Kiem tra mach roi reset.");
      } else {
        Serial.println("[khoi] cam bien khoi san sang");
      }
    }
  }
  if (loiDuongKhoi) {
    if (soCo < SO_PHONG) {                       // đọc được ít nhất 1 phòng sạch: đường đọc đã ổn lại
      loiDuongKhoi = false;
      Serial.println("[khoi] duong doc khoi da binh thuong tro lai");
    } else {
      for (uint8_t i = 0; i < SO_PHONG; i++) coKhoi[i] = false;
    }
  }
  for (uint8_t i = 0; i < SO_PHONG; i++) {
    capNhatKhoi(i, coKhoi[i] || epKhoi[i]);
    inThayDoi(i, now);
  }
}

// ======================= ĐÈN, CÒI, RƠ-LE (TB-06, TB-10, MR-03, MR-04) ===
// Bit trong chuỗi 595: đèn phòng i = 2i, còi = 2i + 1, rơ-le = 20 + i
uint32_t dauRaTruoc = 0xFFFFFFFF;
int8_t   coiChungTruoc = -1;

void ghi595(uint32_t bits) {
  digitalWrite(CHAN_595_LATCH, LOW);
  shiftOut(CHAN_595_DATA, CHAN_595_CLOCK, MSBFIRST, (bits >> 24) & 0xFF); // IC thứ 4 (rơ-le 5-10)
  shiftOut(CHAN_595_DATA, CHAN_595_CLOCK, MSBFIRST, (bits >> 16) & 0xFF); // IC thứ 3
  shiftOut(CHAN_595_DATA, CHAN_595_CLOCK, MSBFIRST, (bits >> 8) & 0xFF);  // IC thứ 2
  shiftOut(CHAN_595_DATA, CHAN_595_CLOCK, MSBFIRST, bits & 0xFF);         // IC thứ 1
  digitalWrite(CHAN_595_LATCH, HIGH);
}

void capNhatDenCoi(uint32_t now) {
  uint32_t bits = 0;
  uint8_t mucCaoNhat = 0;
  bool coLoiLau = false;
  bool nhipCap2Den = (now / 250) % 2 == 0;     // đèn nháy nhanh 250/250 ms
  bool nhipCap2Coi = (now / 500) % 2 == 0;     // còi 500/500 ms
  bool nhipCap3Den = (now / 100) % 2 == 0;     // đèn nháy rất nhanh 100/100 ms
  bool nhipLoiDen  = (now / 1000) % 2 == 0;    // đèn nháy chậm 1 s/1 s
  bool nhipLoiCoi  = (now % 10000) < 100;      // bíp 100 ms mỗi 10 s

  KHOA();
  bool tatTieng = dangTatTieng(now);
  MO_KHOA();
  tatTiengHienTai = tatTieng;

  for (uint8_t i = 0; i < SO_PHONG; i++) {
    KHOA();
    uint8_t m = mucPhong(i);
    bool ll = loiLau(i, now);
    bool nd = ngatDien[i];
    MO_KHOA();
    bool den = false, coi = false;
    if (m == 3)      { den = nhipCap3Den; coi = true; }
    else if (m == 2) { den = nhipCap2Den; coi = nhipCap2Coi; }
    else if (ll)     { den = nhipLoiDen;  coi = nhipLoiCoi; coLoiLau = true; }
    else if (m == 1) { den = true; }                       // CHÚ Ý: sáng liên tục, không còi
    if (m > mucCaoNhat) mucCaoNhat = m;
    if (tatTieng) coi = false;                             // MR-05: đèn vẫn nháy
    if (den) bits |= (1UL << (2 * i));
    if (coi) bits |= (1UL << (2 * i + 1));
    if (nd)  bits |= (1UL << (20 + i));                    // rơ-le pnp: HIGH = ngắt (NC hở)
  }
  if (bits != dauRaTruoc) { ghi595(bits); dauRaTruoc = bits; }

  // Còi hành lang của tầng (MR-06)
  int8_t coiChung = 0;
  if (!tatTieng) {
    if (mucCaoNhat == 3)      coiChung = 1;
    else if (mucCaoNhat == 2) coiChung = nhipCap2Coi ? 1 : 0;
    else if (coLoiLau)        coiChung = nhipLoiCoi ? 1 : 0;
  }
  if (coiChung != coiChungTruoc) {
    if (coiChung) tone(CHAN_COI_CHUNG, TAN_SO_COI);
    else          noTone(CHAN_COI_CHUNG);
    coiChungTruoc = coiChung;
  }
}

// MR-05: cấp lại điện cho mọi phòng đủ điều kiện (đã hết báo động)
void capLaiDienTatCa() {
  uint8_t so = 0;
  KHOA();
  for (uint8_t i = 0; i < SO_PHONG; i++) if (capLaiDien(i)) so++;
  MO_KHOA();
  Serial.printf("Cap lai dien: %u phong (phong con bao dong thi van ngat)\r\n", so);
}

// ======================= LỆNH SERIAL (mục 7.3, 10) ======================
String dongLenh;

int timPhong(const String& ma) {
  for (uint8_t i = 0; i < SO_PHONG; i++) if (ma == DS_PHONG[i]) return i;
  Serial.printf("Phong %s khong thuoc %s\r\n", ma.c_str(), MA_THIET_BI);
  return -1;
}

void inTrangThai() {
  Serial.printf("=== %s | MQTT: %s | tat tieng: %s ===\r\n", MA_THIET_BI,
                mqttDaKetNoi ? "da ket noi" : (mqttTatChuDong ? "tat chu dong" : "chua ket noi"),
                tatTiengHienTai ? "CO" : "-");
  Serial.println("Phong  Nhiet do  Cap          Khoi Loi  Dien   Ghi chu");
  for (uint8_t i = 0; i < SO_PHONG; i++) {
    KHOA();
    float t = nhietDo[i]; bool l = loiCamBien[i]; uint8_t m = mucPhong(i);
    bool k = khoi[i]; bool n = ngatDien[i];
    MO_KHOA();
    String ghiChu = "";
    if (!isnan(giaTriEp[i])) ghiChu += "ep " + String(giaTriEp[i], 1) + "C ";
    if (epLoi[i]) ghiChu += "gia lap loi ";
    if (epKhoi[i]) ghiChu += "gia lap khoi ";
    Serial.printf("%-6s %8s  %-12s %-4s %-4s %-6s %s\r\n", DS_PHONG[i],
                  isnan(t) ? "null" : String(t, 1).c_str(), TEN_MUC[m], k ? "co" : "-",
                  l ? "co" : "-", n ? "NGAT" : "co", ghiChu.c_str());
  }
}

void xuLyLenh(String s) {
  s.trim();
  if (s.length() == 0) return;
  int c1 = s.indexOf(' ');
  String lenh = c1 < 0 ? s : s.substring(0, c1);
  String con  = c1 < 0 ? "" : s.substring(c1 + 1);
  con.trim();
  int c2 = con.indexOf(' ');
  String thamSo1 = c2 < 0 ? con : con.substring(0, c2);
  String thamSo2 = c2 < 0 ? "" : con.substring(c2 + 1);
  lenh.toLowerCase();

  if (lenh == "dat" || lenh == "nhieu") {
    int i = timPhong(thamSo1);
    if (i < 0 || thamSo2.length() == 0) { Serial.println("Cu phap: dat|nhieu <phong> <nhiet_do>"); return; }
    float t = thamSo2.toFloat();
    if (lenh == "dat") giaTriEp[i] = t; else nhieuMotLan[i] = t;
    Serial.printf("OK: %s phong %s = %.1f C\r\n", lenh.c_str(), DS_PHONG[i], t);
  } else if (lenh == "tha") {
    int i = timPhong(thamSo1);
    if (i >= 0) { giaTriEp[i] = NAN; Serial.printf("OK: phong %s doc lai cam bien\r\n", DS_PHONG[i]); }
  } else if (lenh == "loi" || lenh == "hetloi") {
    int i = timPhong(thamSo1);
    if (i >= 0) { epLoi[i] = (lenh == "loi"); Serial.printf("OK: %s phong %s\r\n", lenh.c_str(), DS_PHONG[i]); }
  } else if (lenh == "khoi" || lenh == "hetkhoi") {
    int i = timPhong(thamSo1);
    if (i >= 0) { epKhoi[i] = (lenh == "khoi"); Serial.printf("OK: %s phong %s\r\n", lenh.c_str(), DS_PHONG[i]); }
  } else if (lenh == "tattieng") {
    batTatTieng(millis());
    Serial.printf("OK: tat tieng %u s (den van nhay)\r\n", THOI_GIAN_TAT_TIENG_S);
  } else if (lenh == "capdien") {
    if (thamSo1 == "all" || thamSo1.length() == 0) capLaiDienTatCa();
    else {
      int i = timPhong(thamSo1);
      if (i >= 0) {
        KHOA(); bool ok = capLaiDien(i); MO_KHOA();
        Serial.printf(ok ? "OK: cap lai dien phong %s\r\n" : "Phong %s chua ngat dien hoac con bao dong\r\n", DS_PHONG[i]);
      }
    }
  } else if (lenh == "mqtt") {
    thamSo1.toLowerCase();
    if (thamSo1 == "off") mqttDatTrangThai(false);
    else if (thamSo1 == "on") mqttDatTrangThai(true);
    else Serial.println("Cu phap: mqtt on|off");
  } else if (lenh == "treo") {
    Serial.println("Co y treo vong lap, watchdog se khoi dong lai sau ~5 s ...");
    while (true) { }                                   // K16
  } else if (lenh == "trangthai") {
    inTrangThai();
  } else if (lenh == "khoiraw") {                      // chẩn đoán đường đọc MQ-2
    inKhoiTho = !inKhoiTho;
    inKhoi(khoiThoCuoi);
    Serial.printf("In khoi tho moi khi doi: %s%s\r\n", inKhoiTho ? "BAT" : "TAT",
                  loiDuongKhoi ? " | DANG LOI DUONG DOC KHOI" : "");
  } else {
    Serial.println("Lenh: dat, tha, nhieu, loi, hetloi, khoi, hetkhoi, tattieng, capdien <phong|all>,");
    Serial.println("      mqtt on|off, treo, trangthai, khoiraw");
  }
}

void docSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { xuLyLenh(dongLenh); dongLenh = ""; }
    else if (dongLenh.length() < 64) dongLenh += c;
  }
}

// ======================= NÚT MQTT (TT-05) ===============================
bool     nutTruoc = LOW;
uint32_t nutDoiLuc = 0;

void docNut(uint32_t now) {
  bool n = digitalRead(CHAN_NUT_MQTT);
  if (n != nutTruoc && now - nutDoiLuc > 50) {
    nutDoiLuc = now;
    nutTruoc = n;
    if (n == HIGH) mqttDatTrangThai(mqttTatChuDong);  // đang tắt thì bật, và ngược lại
  }
}

// ======================= NÚT TẮT TIẾNG / CẤP LẠI ĐIỆN (MR-05) ============
bool     nutTTTruoc = HIGH;
uint32_t nutTTDoiLuc = 0;
uint32_t nutTTBamLuc = 0;
bool     daCapDienLanBamNay = false;

void docNutTatTieng(uint32_t now) {
  bool n = digitalRead(CHAN_NUT_TAT_TIENG);
  if (n != nutTTTruoc && now - nutTTDoiLuc > 50) {
    nutTTDoiLuc = now;
    nutTTTruoc = n;
    if (n == LOW) {                          // vừa bấm
      nutTTBamLuc = now;
      daCapDienLanBamNay = false;
    } else if (!daCapDienLanBamNay) {        // nhả ra sau lần bấm ngắn
      batTatTieng(now);
      Serial.printf("[%lu ms] Nut: TAT TIENG %u s (den van nhay)\r\n", (unsigned long)now, THOI_GIAN_TAT_TIENG_S);
    }
  }
  if (n == LOW && !daCapDienLanBamNay && now - nutTTBamLuc >= THOI_GIAN_GIU_CAP_DIEN_MS) {
    daCapDienLanBamNay = true;               // giữ 3 s: cấp lại điện, không tính là tắt tiếng
    capLaiDienTatCa();
  }
}

// ======================= WATCHDOG (TB-12) ===============================
void batWatchdog() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  esp_task_wdt_config_t cfg = {};
  cfg.timeout_ms = WDT_TIMEOUT_S * 1000;
  cfg.idle_core_mask = 0;
  cfg.trigger_panic = true;
  if (esp_task_wdt_reconfigure(&cfg) != ESP_OK) esp_task_wdt_init(&cfg);
#else
  esp_task_wdt_init(WDT_TIMEOUT_S, true);
#endif
  esp_task_wdt_add(NULL);   // theo dõi task chạy setup()/loop()
}

// ======================= GIÁM SÁT (NF-04, NF-05) ========================
uint32_t vongLapMax = 0;
uint32_t lanInGiamSat = 0;

// ======================= SETUP / LOOP ===================================
void setup() {
  Serial.begin(115200);
  delay(100);
  esp_reset_reason_t lyDo = esp_reset_reason();
  Serial.printf("\r\n=== CanhBaoChay v1.2 %s khoi dong (ly do reset: %d%s) ===\r\n", MA_THIET_BI, (int)lyDo,
                (lyDo == ESP_RST_TASK_WDT || lyDo == ESP_RST_PANIC || lyDo == ESP_RST_INT_WDT)
                    ? " - watchdog" : "");

  khoiTaoLogic();
  for (uint8_t i = 0; i < SO_PHONG; i++) {
    dht[i].setup(CHAN_DHT[i], DHTesp::DHT22);
    giaTriEp[i] = NAN; nhieuMotLan[i] = NAN; epLoi[i] = false; epKhoi[i] = false;
    mucTruoc[i] = 0; loiTruoc[i] = false; ngatTruoc[i] = false; loiDht[i] = "";
  }

  pinMode(CHAN_595_DATA, OUTPUT);
  pinMode(CHAN_595_CLOCK, OUTPUT);
  pinMode(CHAN_595_LATCH, OUTPUT);
  pinMode(CHAN_165_PL, OUTPUT);
  pinMode(CHAN_165_CP, OUTPUT);
  pinMode(CHAN_165_Q7, INPUT);
  digitalWrite(CHAN_165_PL, HIGH);
  digitalWrite(CHAN_165_CP, LOW);
  pinMode(CHAN_NUT_MQTT, INPUT);
  pinMode(CHAN_NUT_TAT_TIENG, INPUT_PULLUP);
  pinMode(CHAN_COI_CHUNG, OUTPUT);
  ghi595(0);                // mọi rơ-le thả: phòng có điện qua tiếp điểm NC
  dauRaTruoc = 0;

  batWatchdog();
  mqttBatDau();             // task MQTT riêng (Task 2)
  Serial.println("Go 'trangthai' de xem bang phong, 'help' de xem lenh.");
}

void loop() {
  uint32_t batDau = millis();
  esp_task_wdt_reset();

  // TB-01: đọc nhiệt xoay vòng, mỗi phòng một lần mỗi ~2 s
  if (batDau - lanDocCuoi >= KHOANG_DOC_MS) {
    lanDocCuoi = batDau;
    docMotPhong(phongKeTiep);
    phongKeTiep = (phongKeTiep + 1) % SO_PHONG;
  }
  // MR-01: đọc 10 cảm biến khói mỗi 0,5 s
  if (batDau - lanDocKhoi >= CHU_KY_DOC_KHOI_MS) {
    lanDocKhoi = batDau;
    docKhoi();
  }

  uint32_t now = millis();
  capNhatDenCoi(now);
  docNut(now);
  docNutTatTieng(now);
  docSerial();

  uint32_t thoiGian = millis() - batDau;
  if (thoiGian > vongLapMax) vongLapMax = thoiGian;
  if (now - lanInGiamSat >= 10000) {
    lanInGiamSat = now;
    Serial.printf("[giam sat] vong lap max %lu ms | heap trong %u B | MQTT %s\r\n",
                  (unsigned long)vongLapMax, (unsigned)ESP.getFreeHeap(),
                  mqttDaKetNoi ? "OK" : "mat");
    vongLapMax = 0;
  }
  // ~100 vòng/giây là đủ cho nhịp đèn 100–250 ms. Vòng lặp dày hơn chỉ tốn CPU, và trên
  // Wokwi làm mô phỏng chạy chậm hơn thời gian thật (phòng bị MẤT KẾT NỐI oan).
  delay(10);
}
