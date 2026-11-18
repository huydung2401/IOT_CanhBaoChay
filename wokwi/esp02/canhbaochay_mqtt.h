/*
 * CanhBaoChay - Phần truyền thông MQTT (Task 2)
 * Đặc tả: SRS CanhBaoChay v1.2, yêu cầu TT-01 .. TT-06, MR-07, MR-08, mục 4.1, 4.2, 10.2
 *
 * Cách dùng: #include file này trong canhbaochay_esp32.ino SAU khi đã khai báo
 * MA_THIET_BI, DS_PHONG, SO_PHONG, các mảng trạng thái, mucPhong(), KHOA()/MO_KHOA(),
 * tatTiengHienTai, CHU_KY_GUI_MS, CHU_KY_NOI_LAI_MS. Gọi mqttBatDau() trong setup().
 *
 * Toàn bộ kết nối chạy trong task FreeRTOS "mqtt" ở core 0, nên connect()
 * có treo vài giây thì loop() (đèn, còi) ở core 1 vẫn chạy bình thường.
 */
#pragma once
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>

// ---------- Cấu hình mạng ----------
const char*    WIFI_SSID     = "Wokwi-GUEST";
const char*    WIFI_MAT_KHAU = "";
const int      WIFI_KENH     = 6;            // kênh của Wokwi-GUEST, nối nhanh hơn
// ĐỔI dãy số 73915 thành dãy riêng của nhóm (giống hệt trong Node-RED)
const char*    TIEN_TO_TOPIC = "canhbaochay_HUIT73915/nhatro01";

// ---------- Broker (MR-08) ----------
// Để TRỐNG tên đăng nhập: dùng broker công cộng, không mã hoá (mặc định, chạy ngay).
// Điền tài khoản broker riêng (ví dụ HiveMQ Cloud bản miễn phí): tự chuyển sang TLS cổng 8883.
const char*    MQTT_TEN_DANG_NHAP = "";
const char*    MQTT_MAT_KHAU      = "";
const char*    MQTT_MAY_CHU_RIENG = "xxxxxxxx.s1.eu.hivemq.cloud";   // địa chỉ cluster của nhóm
const uint16_t MQTT_CONG_TLS      = 8883;
const char*    MQTT_MAY_CHU_CONG_CONG = "broker.emqx.io";   // broker.hivemq.com đo được mất 30-50% tin
const uint16_t MQTT_CONG_CONG_CONG    = 1883;

// Chứng chỉ gốc ISRG Root X1 (Let's Encrypt), hạn 2035, SHA-256 96:BC:EC:06:...:08:C6.
// HiveMQ Cloud và phần lớn broker dùng Let's Encrypt đều xác thực được bằng chứng chỉ này.
static const char CA_ISRG_ROOT_X1[] PROGMEM =
"-----BEGIN CERTIFICATE-----\n"
"MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw\n"
"TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh\n"
"cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4\n"
"WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu\n"
"ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY\n"
"MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc\n"
"h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+\n"
"0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U\n"
"A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW\n"
"T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH\n"
"B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC\n"
"B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv\n"
"KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn\n"
"OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn\n"
"jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw\n"
"qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI\n"
"rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV\n"
"HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq\n"
"hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL\n"
"ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ\n"
"3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK\n"
"NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5\n"
"ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur\n"
"TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC\n"
"jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc\n"
"oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq\n"
"4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA\n"
"mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d\n"
"emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=\n"
"-----END CERTIFICATE-----\n";

// ---------- Giờ NTP (MR-07) ----------
const long MUI_GIO_GIAY = 7 * 3600;          // UTC+7

// ---------- Trạng thái ----------
volatile bool mqttTatChuDong = false;   // TT-05: người demo đang ngắt MQTT
volatile bool mqttDaKetNoi   = false;

static WiFiClient       mqttClientThuong;
static WiFiClientSecure mqttClientTls;
static PubSubClient     mqttClient;

static uint32_t seqGui[SO_PHONG];         // TT-06: bộ đếm riêng từng phòng, về 0 khi reset
static uint16_t daGuiDauHieu[SO_PHONG];   // trạng thái đã gửi gần nhất (để phát hiện thay đổi)
static bool     daGuiLanNao[SO_PHONG];

static bool dungTls() { return MQTT_TEN_DANG_NHAP[0] != '\0'; }

void mqttDatTrangThai(bool bat) {
  mqttTatChuDong = !bat;
  Serial.printf("[mqtt] %s chu dong\r\n", bat ? "BAT" : "TAT");
}

// Giây epoch hiện tại, 0 nếu chưa đồng bộ NTP
static uint32_t gioHienTai() {
  time_t t = time(nullptr);
  return (t > 1700000000) ? (uint32_t)t : 0;
}

// Gói các trường quyết định "trạng thái đổi" thành 1 số (TT-04 mở rộng cho MR-02..MR-05)
static uint16_t dauHieu(uint8_t muc, bool lo, bool kh, bool nd, bool tt) {
  return (uint16_t)(muc | (lo << 2) | (kh << 3) | (nd << 4) | (tt << 5));
}

// Gửi tin của phòng i theo mẫu JSON mục 4.2 + 10.2. Trả về true nếu publish thành công.
static bool mqttGuiPhong(uint8_t i) {
  KHOA();
  float   t  = nhietDo[i];
  bool    lo = loiCamBien[i];
  uint8_t mc = mucPhong(i);
  bool    kh = khoi[i];
  bool    nd = ngatDien[i];
  MO_KHOA();
  bool tt = tatTiengHienTai;

  char topic[96];
  snprintf(topic, sizeof(topic), "%s/phong/%s/dulieu", TIEN_TO_TOPIC, DS_PHONG[i]);

  char nhiet[12];
  if (lo || isnan(t)) strcpy(nhiet, "null");
  else snprintf(nhiet, sizeof(nhiet), "%.1f", t);

  char json[256];
  snprintf(json, sizeof(json),
           "{\"ma_thiet_bi\":\"%s\",\"ma_phong\":\"%s\",\"nhiet_do\":%s,"
           "\"bao_dong\":%s,\"loi_cam_bien\":%s,\"seq\":%lu,"
           "\"muc\":%u,\"khoi\":%s,\"ngat_dien\":%s,\"tat_tieng\":%s,\"ts\":%lu}",
           MA_THIET_BI, DS_PHONG[i], nhiet, mc >= 2 ? "true" : "false", lo ? "true" : "false",
           (unsigned long)seqGui[i], mc, kh ? "true" : "false", nd ? "true" : "false",
           tt ? "true" : "false", (unsigned long)gioHienTai());

  if (!mqttClient.publish(topic, json)) return false;   // QoS 0, retain = false
  seqGui[i]++;
  daGuiDauHieu[i] = dauHieu(mc, lo, kh, nd, tt);
  daGuiLanNao[i]  = true;
  return true;
}

static void mqttGuiTatCa() {
  for (uint8_t i = 0; i < SO_PHONG; i++) mqttGuiPhong(i);
}

static void mqttTask(void*) {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_MAT_KHAU, WIFI_KENH);
  Serial.printf("[wifi] dang ket noi %s ...\r\n", WIFI_SSID);

  const char* mayChu = dungTls() ? MQTT_MAY_CHU_RIENG : MQTT_MAY_CHU_CONG_CONG;
  uint16_t    cong   = dungTls() ? MQTT_CONG_TLS : MQTT_CONG_CONG_CONG;
  if (dungTls()) {
    mqttClientTls.setCACert(CA_ISRG_ROOT_X1);
    mqttClient.setClient(mqttClientTls);
  } else {
    mqttClient.setClient(mqttClientThuong);
  }
  mqttClient.setServer(mayChu, cong);
  mqttClient.setBufferSize(512);
  mqttClient.setSocketTimeout(dungTls() ? 5 : 2);   // bắt tay TLS lâu hơn
  // Wokwi thường chạy chậm hơn thời gian thật (thanh tốc độ < 100%). Keepalive tính theo
  // millis() mô phỏng nên 10 s dễ bị broker cắt; 60 s an toàn mà vẫn phát hiện rớt mạng.
  mqttClient.setKeepAlive(60);

  char clientId[64];
  // TT-01. Thêm 4 số ngẫu nhiên: hai máy cùng chạy project (clone từ Git) không bị broker
  // đá nhau ra vì trùng client ID. Topic vẫn chung nên hai máy sẽ thấy dữ liệu của nhau.
  snprintf(clientId, sizeof(clientId), "canhbaochay_HUIT73915_%s_%04X", MA_THIET_BI, (unsigned)(esp_random() & 0xFFFF));

  uint32_t lanThuWifi = millis();
  uint32_t lanThuMqtt = 0;
  uint32_t lanGuiCuoi = 0;
  uint8_t  phongGuiKeTiep = 0;
  bool     wifiTruoc  = false;
  bool     daCauHinhGio = false;

  for (;;) {
    uint32_t now = millis();

    // TT-05: ngắt chủ động
    if (mqttTatChuDong) {
      if (mqttClient.connected()) {
        mqttClient.disconnect();
        Serial.println("[mqtt] da ngat theo lenh");
      }
      mqttDaKetNoi = false;
      lanThuMqtt = 0;                       // bật lại thì nối ngay
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }

    // Wi-Fi
    if (WiFi.status() != WL_CONNECTED) {
      mqttDaKetNoi = false;
      if (wifiTruoc) { Serial.println("[wifi] mat ket noi"); wifiTruoc = false; }
      if (now - lanThuWifi >= CHU_KY_NOI_LAI_MS) {    // TT-02
        lanThuWifi = now;
        Serial.println("[wifi] thu ket noi lai ...");
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_MAT_KHAU, WIFI_KENH);
      }
      vTaskDelay(pdMS_TO_TICKS(100));
      continue;
    }
    if (!wifiTruoc) {
      wifiTruoc = true;
      Serial.printf("[wifi] da ket noi, IP %s\r\n", WiFi.localIP().toString().c_str());
      if (!daCauHinhGio) {                   // MR-07: đồng bộ giờ, chạy nền
        configTime(MUI_GIO_GIAY, 0, "pool.ntp.org", "time.google.com");
        daCauHinhGio = true;
      }
    }

    // MQTT
    if (!mqttClient.connected()) {
      if (mqttDaKetNoi) Serial.println("[mqtt] mat ket noi broker");
      mqttDaKetNoi = false;
      if (lanThuMqtt == 0 || now - lanThuMqtt >= CHU_KY_NOI_LAI_MS) {   // TT-02
        lanThuMqtt = now;
        Serial.printf("[mqtt] ket noi %s:%u%s ...\r\n", mayChu, cong, dungTls() ? " (TLS)" : "");
        bool ok = dungTls() ? mqttClient.connect(clientId, MQTT_TEN_DANG_NHAP, MQTT_MAT_KHAU)
                            : mqttClient.connect(clientId);
        if (ok) {
          Serial.println("[mqtt] da ket noi, gui trang thai tat ca phong");
          mqttDaKetNoi = true;
          mqttGuiTatCa();                     // DB-04: dashboard cập nhật ngay
          lanGuiCuoi = millis();
        } else {
          // -2: không tới được máy chủ/TLS hỏng; 4/5: sai tài khoản hoặc không có quyền
          Serial.printf("[mqtt] that bai, ma loi %d; thu lai sau %lu ms\r\n",
                        mqttClient.state(), (unsigned long)CHU_KY_NOI_LAI_MS);
        }
      }
      vTaskDelay(pdMS_TO_TICKS(100));
      continue;
    }

    mqttClient.loop();
    mqttDaKetNoi = true;

    // TT-04 (mở rộng): gửi ngay khi cấp, lỗi, khói, ngắt điện hoặc tắt tiếng đổi
    bool tt = tatTiengHienTai;
    for (uint8_t i = 0; i < SO_PHONG; i++) {
      KHOA();
      uint16_t dh = dauHieu(mucPhong(i), loiCamBien[i], khoi[i], ngatDien[i], tt);
      MO_KHOA();
      if (!daGuiLanNao[i] || dh != daGuiDauHieu[i]) mqttGuiPhong(i);
    }

    // TT-03: gửi định kỳ, RẢI ĐỀU từng phòng (mỗi CHU_KY_GUI_MS / SO_PHONG = 500 ms một phòng)
    // để mỗi phòng vẫn 5 s một tin. Gửi dồn 10 tin một lúc thì broker công cộng /
    // cổng mạng Wokwi hay đánh rơi, phòng bị báo MẤT KẾT NỐI oan.
    if (now - lanGuiCuoi >= CHU_KY_GUI_MS / SO_PHONG) {
      lanGuiCuoi = now;
      mqttGuiPhong(phongGuiKeTiep);
      phongGuiKeTiep = (phongGuiKeTiep + 1) % SO_PHONG;
    }

    vTaskDelay(pdMS_TO_TICKS(50));   // đổi trạng thái vẫn gửi trong <= 50 ms
  }
}

void mqttBatDau() {
  for (uint8_t i = 0; i < SO_PHONG; i++) {
    seqGui[i] = 0; daGuiDauHieu[i] = 0; daGuiLanNao[i] = false;
  }
  // TLS cần thêm bộ nhớ ngăn xếp cho bắt tay mbedTLS
  xTaskCreatePinnedToCore(mqttTask, "mqtt", dungTls() ? 12288 : 8192, NULL, 1, NULL, 0);
}
