#!/usr/bin/env python3
"""
Sinh hai project Wokwi (esp01, esp02) từ một bản code duy nhất (TB-09).

Mỗi thư mục wokwi/espXX/ gồm:
  canhbaochay_esp32.ino  (bản sao, chỉ khác dòng SO_THIET_BI)
  canhbaochay_mqtt.h     (bản sao nguyên văn)
  diagram.json           (mạch v1.2: 10 DHT22, 10 cảm biến khói MQ-2, 2 x 74HC165,
                          4 x 74HC595, 10 đèn, 10 còi, 10 rơ-le + đèn "điện phòng",
                          2 công tắc lỗi, nút MQTT, nút tắt tiếng, còi chung)
  libraries.txt          (thư viện Wokwi tự cài)

Chạy lại script mỗi khi sửa code trong canhbaochay_esp32/:
  python3 wokwi/tao_wokwi.py
"""
import json, pathlib, re

GOC = pathlib.Path(__file__).resolve().parent.parent
CODE = GOC / "canhbaochay_esp32"

# Chân ESP32 theo mục 7.1, tên chân của linh kiện wokwi-esp32-devkit-v1
CHAN_DHT = ["D19", "RX2", "TX2", "D21", "D22", "D25", "D26", "D27", "D32", "D33"]  # GPIO 19,16,17,21,22,25,26,27,32,33
PHONG_CO_CONG_TAC = [2, 3]   # phòng thứ 3 và 4 (103, 104 / 113, 114) có công tắc trên dây DATA

DO, DEN, XANH, VANG, CAM, TIM = "red", "black", "green", "gold", "orange", "purple"


def tao_diagram(ds_phong):
    parts, conns = [], []

    def part(loai, id_, left, top, attrs=None, rotate=None):
        p = {"type": loai, "id": id_, "top": top, "left": left, "attrs": attrs or {}}
        if rotate is not None:
            p["rotate"] = rotate
        parts.append(p)

    def noi(a, b, mau):
        conns.append([a, b, mau, []])

    part("wokwi-esp32-devkit-v1", "esp", -40, 180)
    noi("esp:TX0", "$serialMonitor:RX", "", )
    noi("esp:RX0", "$serialMonitor:TX", "")

    x0, buoc = 140, 90
    for i, ma in enumerate(ds_phong):
        x = x0 + i * buoc
        # Cảm biến
        part("wokwi-dht22", f"dht{ma}", x, -190, {"temperature": "28", "humidity": "60"})
        noi(f"dht{ma}:VCC", "esp:3V3", DO)
        noi(f"dht{ma}:GND", "esp:GND.1", DEN)
        if i in PHONG_CO_CONG_TAC:
            part("wokwi-slide-switch", f"sw{ma}", x + 5, -70)
            noi(f"dht{ma}:SDA", f"sw{ma}:2", XANH)
            noi(f"sw{ma}:1", f"esp:{CHAN_DHT[i]}", XANH)
        else:
            noi(f"dht{ma}:SDA", f"esp:{CHAN_DHT[i]}", XANH)
        # Đèn và còi của phòng
        part("wokwi-led", f"den{ma}", x + 10, 380, {"color": "red", "label": ma})
        part("wokwi-buzzer", f"coi{ma}", x, 460, {"volume": "0.1"})
        noi(f"den{ma}:C", "esp:GND.2", DEN)
        noi(f"coi{ma}:1", "esp:GND.2", DEN)

    # 4 IC 74HC595 nối chuỗi: DS <- GPIO23, SHCP <- GPIO18, STCP <- GPIO5
    for k in range(4):
        sr = f"sr{k + 1}"
        part("wokwi-74hc595", sr, 180 + k * 230, 200)
        noi(f"{sr}:VCC", "esp:3V3", DO)
        noi(f"{sr}:MR", "esp:3V3", DO)
        noi(f"{sr}:GND", "esp:GND.2", DEN)
        noi(f"{sr}:OE", "esp:GND.2", DEN)
        noi(f"{sr}:SHCP", "esp:D18", VANG)
        noi(f"{sr}:STCP", "esp:D5", CAM)
        noi(f"{sr}:DS", "esp:D23" if k == 0 else f"sr{k}:Q7S", TIM)

    # Bit 2i = đèn, 2i+1 = còi của phòng i, 20+i = rơ-le phòng i; mỗi IC 8 bit
    for i, ma in enumerate(ds_phong):
        for bit, chan in ((2 * i, f"den{ma}:A"), (2 * i + 1, f"coi{ma}:2"), (20 + i, f"rl{ma}:IN")):
            noi(f"sr{bit // 8 + 1}:Q{bit % 8}", chan, XANH)

    # MR-02: cảm biến khói MQ-2 mỗi phòng (chân Wokwi: AOUT, DOUT), DOUT xuống LOW khi khói vượt ngưỡng.
    # 2 IC 74HC165 nối chuỗi: PL <- GPIO4, CP <- GPIO13, Q7 của IC2 -> GPIO35 (chỉ vào).
    # IC1 D0..D7 = phòng thứ 1..8, IC2 D0..D1 = phòng thứ 9..10 (IC2 được đọc trước).
    for k in range(2):
        pi = f"pi{k + 1}"
        part("wokwi-74hc165", pi, 300 + k * 420, 60)
        noi(f"{pi}:VCC", "esp:3V3", DO)
        noi(f"{pi}:GND", "esp:GND.2", DEN)
        noi(f"{pi}:CE", "esp:GND.2", DEN)
        noi(f"{pi}:PL", "esp:D4", CAM)
        noi(f"{pi}:CP", "esp:D13", VANG)
    noi("pi1:Q7", "pi2:DS", TIM)
    noi("pi2:Q7", "esp:D35", TIM)
    noi("pi1:DS", "esp:GND.2", DEN)
    for d in range(2, 8):                  # chân IC2 không dùng: kéo lên = "không khói"
        noi(f"pi2:D{d}", "esp:3V3", DO)
    for i, ma in enumerate(ds_phong):
        x = x0 + i * buoc
        part("wokwi-gas-sensor", f"khoi{ma}", x - 10, -330, {"ppm": "100"})
        noi(f"khoi{ma}:VCC", "esp:VIN", DO)
        noi(f"khoi{ma}:GND", "esp:GND.1", DEN)
        noi(f"khoi{ma}:DOUT", f"pi{i // 8 + 1}:D{i % 8}", XANH)

    # MR-04: rơ-le ngắt điện phòng (pnp: IN thấp = COM nối NC = có điện)
    # Đèn vàng "điện phòng" sáng = phòng đang có điện; tắt = đã ngắt.
    for i, ma in enumerate(ds_phong):
        x = x0 + i * buoc
        y = 560 + (i % 2) * 110             # so le 2 hàng cho khỏi chồng nhau
        part("wokwi-relay-module", f"rl{ma}", x - 20, y, {"transistor": "pnp"}, rotate=90)
        part("wokwi-led", f"dien{ma}", x + 40, y + 10, {"color": "yellow", "label": f"điện {ma}"})
        noi(f"rl{ma}:VCC", "esp:VIN", DO)
        noi(f"rl{ma}:GND", "esp:GND.2", DEN)
        noi(f"rl{ma}:COM", "esp:3V3", DO)
        noi(f"rl{ma}:NC", f"dien{ma}:A", VANG)
        noi(f"dien{ma}:C", "esp:GND.2", DEN)

    # MR-05: nút TẮT TIẾNG (GPIO15, INPUT_PULLUP). Bấm ngắn = tắt còi 5 phút,
    # giữ 3 s = cấp lại điện các phòng đã an toàn.
    part("wokwi-pushbutton", "nutTatTieng", -230, 440, {"color": "yellow", "label": "Tắt tiếng / giữ 3s cấp điện"})
    noi("nutTatTieng:1.r", "esp:D15", XANH)
    noi("nutTatTieng:2.r", "esp:GND.1", DEN)

    # Nút bật/tắt MQTT: GPIO34 (chỉ vào) + điện trở 10k kéo xuống GND, bấm nối 3V3
    part("wokwi-pushbutton", "nutMqtt", -230, 220, {"color": "blue", "label": "MQTT on/off"})
    part("wokwi-resistor", "rNut", -235, 290, {"value": "10000"})
    noi("nutMqtt:1.r", "esp:D34", XANH)
    noi("nutMqtt:2.r", "esp:3V3", DO)
    noi("rNut:1", "esp:D34", XANH)
    noi("rNut:2", "esp:GND.1", DEN)
    # Còi chung (GPIO2) phát tiếng bằng tone()
    part("wokwi-buzzer", "coiChung", -220, 360, {"volume": "0.2"})
    noi("coiChung:2", "esp:D2", XANH)
    noi("coiChung:1", "esp:GND.1", DEN)

    return {"version": 1, "author": "Nhom CanhBaoChay", "editor": "wokwi",
            "parts": parts, "connections": conns, "dependencies": {}}


def main():
    ino = (CODE / "canhbaochay_esp32.ino").read_text(encoding="utf-8")
    mqtt = (CODE / "canhbaochay_mqtt.h").read_text(encoding="utf-8")
    for so, ma_tb, phong_dau in ((1, "esp01", 101), (2, "esp02", 111)):
        thu_muc = GOC / "wokwi" / ma_tb
        thu_muc.mkdir(parents=True, exist_ok=True)
        ino_tb, n = re.subn(r"#define SO_THIET_BI \d+", f"#define SO_THIET_BI {so}", ino, count=1)
        assert n == 1
        (thu_muc / "canhbaochay_esp32.ino").write_text(ino_tb, encoding="utf-8")
        (thu_muc / "canhbaochay_mqtt.h").write_text(mqtt, encoding="utf-8")
        (thu_muc / "libraries.txt").write_text(
            "# Wokwi tu cai cac thu vien nay\nPubSubClient\nDHT sensor library for ESPx\n", encoding="utf-8")
        ds = [str(phong_dau + i) for i in range(10)]
        (thu_muc / "diagram.json").write_text(
            json.dumps(tao_diagram(ds), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Da tao {thu_muc.relative_to(GOC)} (phong {ds[0]}-{ds[-1]})")


if __name__ == "__main__":
    main()
