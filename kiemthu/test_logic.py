#!/usr/bin/env python3
"""
Kiểm thử logic báo động của canhbaochay_esp32.ino trên máy tính (không cần ESP32).

Script trích nguyên văn phần cấu hình và đoạn "=== BAT DAU LOGIC BAO DONG ===" ...
"=== KET THUC LOGIC BAO DONG ===" từ file .ino, ghép với các ca kiểm thử bên dưới,
biên dịch bằng g++ rồi chạy. Như vậy logic được kiểm chính là logic nạp lên ESP32.

Chạy:  python3 kiemthu/test_logic.py
"""
import pathlib, re, subprocess, sys, tempfile

GOC = pathlib.Path(__file__).resolve().parent.parent
INO = GOC / "canhbaochay_esp32" / "canhbaochay_esp32.ino"
src = INO.read_text(encoding="utf-8")

def doan(bat_dau, ket_thuc):
    m = re.search(re.escape(bat_dau) + r"(.*?)" + re.escape(ket_thuc), src, re.S)
    if not m:
        sys.exit(f"Khong tim thay doan {bat_dau!r}")
    return m.group(1)

cau_hinh = doan("// ======================= CẤU HÌNH CHUNG", "// ======================= RIÊNG TỪNG THIẾT BỊ")
cau_hinh = cau_hinh.split("\n", 1)[1]
logic = doan("// === BAT DAU LOGIC BAO DONG", "// === KET THUC LOGIC BAO DONG ===")
logic = logic.split("\n", 1)[1]

PRELUDE = r"""
#include <cstdint>
#include <cmath>
#include <cstdio>
#include <algorithm>
using std::min; using std::isnan;
#define KHOA()
#define MO_KHOA()
#define SO_PHONG 10
float nhietDo[SO_PHONG]; bool loiCamBien[SO_PHONG]; bool baoDong[SO_PHONG];
bool khoi[SO_PHONG]; bool chuY[SO_PHONG]; bool ngatDien[SO_PHONG];
"""

TESTS = r"""
static int loi = 0, dat = 0;
static uint32_t now = 0;
#define KIEM(dieukien, mota) do { if (dieukien) { dat++; printf("  DAT   %s\n", mota); } \
                                  else { loi++; printf("  KHONG %s\n", mota); } } while (0)
// Đọc phòng 0 với nhiệt độ t, mỗi lần cách nhau CHU_KY_DOC_MS
static void doc(float t, int lan = 1) { for (int k = 0; k < lan; k++) { now += CHU_KY_DOC_MS; capNhatBaoDong(0, t, now); } }
// Đọc MQ-2 phòng 0, mỗi lần cách nhau CHU_KY_DOC_KHOI_MS
static void docKhoi(bool co, int lan = 1) { for (int k = 0; k < lan; k++) { now += CHU_KY_DOC_KHOI_MS; capNhatKhoi(0, co); } }
static void batDau(const char* ten) { khoiTaoLogic(); now = 100000; printf("%s\n", ten); }

int main() {
  batDau("K1/K2 - vuot nguong 45 C");
  doc(30, 10);
  KIEM(!baoDong[0], "30 C: binh thuong");
  doc(47);
  KIEM(!baoDong[0], "lan doc 47 C dau tien: chua bat (TB-03 can 2 lan)");
  doc(47);
  KIEM(baoDong[0], "lan doc 47 C thu hai: BAO DONG");
  KIEM(!baoDongDoTang[0], "ghi nhan bat do nguong, khong phai do tang nhanh");

  batDau("K14 - nhieu mot lan doc");
  doc(30, 10); doc(47); doc(30, 3);
  KIEM(!baoDong[0], "mot lan 47 C roi ve 30 C: khong bao dong");

  batDau("K4/K5 - hysteresis");
  doc(30, 5); doc(47, 2);
  doc(42, 3);
  KIEM(baoDong[0], "42 C (vung giua): van BAO DONG");
  doc(40.1);
  KIEM(baoDong[0], "40.1 C: van BAO DONG");
  doc(38);
  KIEM(!baoDong[0], "38 C: het bao dong");

  batDau("K11 - bien nguong");
  doc(44.9, 5);
  KIEM(!baoDong[0], "44.9 C x5: khong bat");
  doc(45.0, 2);
  KIEM(baoDong[0], "45.0 C x2: bat");
  doc(40.1, 2);
  KIEM(baoDong[0], "40.1 C: van bat");
  doc(40.0);
  KIEM(!baoDong[0], "40.0 C: tat");

  batDau("K9 - loi cam bien khi dang bao dong");
  doc(30, 5); doc(47, 2);
  doc(NAN);
  KIEM(!loiCamBien[0] && baoDong[0], "1 lan doc hong le te: bo qua, chua bao loi");
  doc(NAN);
  KIEM(baoDong[0] && loiCamBien[0], "2 lan doc hong lien tiep: van bao dong, co loi");
  KIEM(std::isnan(nhietDo[0]), "nhiet do = NAN (JSON null)");
  doc(NAN, 14);   // 28 s kể từ lúc xác nhận lỗi
  KIEM(!loiLau(0, now), "loi 28 s: chua bao loi tai cho");
  doc(NAN, 2);    // 32 s
  KIEM(loiLau(0, now), "loi 32 s: bao loi tai cho (TB-10)");
  KIEM(baoDong[0], "loi keo dai van khong xoa bao dong (TB-05)");
  doc(30, 1);
  KIEM(!loiCamBien[0] && !loiLau(0, now), "doc lai duoc: het loi");
  KIEM(!baoDong[0], "doc lai 30 C: het bao dong theo nguong tat");

  batDau("K9 - loi cam bien khong tu bat bao dong");
  doc(30, 5); doc(NAN, 20);
  KIEM(!baoDong[0], "loi khi dang binh thuong: khong bat bao dong");
  doc(30); doc(NAN); doc(NAN, 3);
  KIEM(loiCamBien[0] && !baoDong[0], "loi xac nhan khi dang binh thuong: van khong bao dong");
  batDau("Doc hong le te xen giua 2 lan 47 C");
  doc(30, 5); doc(47); doc(NAN); doc(47);
  KIEM(baoDong[0] && !loiCamBien[0], "47, hong 1 lan, 47: van bao dong (lan hong bi bo qua)");

  batDau("K15 - tang nhanh 9 C trong 30 s");
  doc(30, 15);    // 30 s ở 30 C
  doc(39);
  KIEM(!baoDong[0], "lan doc 39 C dau tien: chua bat");
  doc(39);
  KIEM(baoDong[0] && baoDongDoTang[0], "lan doc 39 C thu hai: BAO DONG do tang nhanh");
  doc(39, 25);    // giữ thêm 50 s, tổng ~54 s kể từ lúc bật
  KIEM(baoDong[0], "39 C trong 60 s dau: van giu bao dong");
  doc(39, 5);     // > 60 s
  KIEM(!baoDong[0], "sau 60 s, 39 C <= 40 C: het bao dong");

  batDau("TB-11 - tang cham khong bao nham");
  for (int k = 0; k < 70; k++) doc(30 + k * 0.2f);   // 0.2 C moi 2 s = 6 C/phut, 30 -> 43.8 C
  KIEM(!baoDong[0], "tang 6 C/phut den 43.8 C: khong bao dong");

  batDau("K16 - sau khoi dong lai, phong van nong");
  uint32_t t0 = now;
  doc(47, 2);
  KIEM(baoDong[0] && (now - t0) <= 5000, "bao dong lai trong <= 5 s (2 lan doc)");


  // ================= v1.2 =================
  batDau("K20 - cap CHU Y 38 C");
  for (int k = 0; k <= 40; k++) doc(30 + k * 0.2f);   // tang cham 30 -> 38 C (khong kich tang nhanh)
  doc(30 + 39 * 0.2f);   // ve 37.8 C de dem lai tu dau
  doc(39);
  KIEM(mucPhong(0) == 0, "lan doc 39 C dau tien: chua CHU Y");
  doc(39);
  KIEM(mucPhong(0) == 1 && !baoDong[0], "lan doc 39 C thu hai: CHU Y (cap 1), chua bao dong");
  KIEM(!ngatDien[0], "CHU Y khong ngat dien");
  doc(37, 3);
  KIEM(mucPhong(0) == 1, "37 C (giua 36 va 38): van CHU Y");
  doc(36);
  KIEM(mucPhong(0) == 0, "36 C: het CHU Y");

  batDau("K21 - khoi MQ-2 xac nhan 2 lan");
  docKhoi(false, 4); docKhoi(true);
  KIEM(!khoi[0], "1 lan co khoi: chua xac nhan");
  docKhoi(false); docKhoi(true);
  KIEM(!khoi[0], "co - khong - co: van chua (nhieu le te)");
  docKhoi(true);
  KIEM(khoi[0] && mucPhong(0) == 2, "2 lan lien tiep co khoi: BAO DONG (cap 2)");
  KIEM(!ngatDien[0], "chi co khoi, nhiet binh thuong: KHONG ngat dien");
  docKhoi(false);
  KIEM(khoi[0], "1 lan het khoi: van giu");
  docKhoi(false);
  KIEM(!khoi[0] && mucPhong(0) == 0, "2 lan het khoi: tro ve binh thuong");

  batDau("K22 - khoi + nhiet = NGUY HIEM, ngat dien");
  for (int k = 0; k <= 45; k++) doc(30 + k * 0.2f);   // tang cham den 39 C: CHU Y
  docKhoi(true, 2);
  KIEM(mucPhong(0) == 3, "khoi + CHU Y: NGUY HIEM (cap 3)");
  KIEM(ngatDien[0], "cap 3: ngat dien");
  batDau("K23 - bao dong nhiet ngat dien va chot");
  doc(30, 5); doc(47, 2);
  KIEM(mucPhong(0) == 2 && ngatDien[0], "bao dong nhiet: cap 2, ngat dien");
  KIEM(!capLaiDien(0) && ngatDien[0], "dang bao dong: khong cho cap lai dien");
  doc(35, 3);
  KIEM(mucPhong(0) == 0 && ngatDien[0], "het bao dong: dien VAN ngat (chot)");
  KIEM(capLaiDien(0) && !ngatDien[0], "het bao dong + giu nut: cap lai dien");
  KIEM(!capLaiDien(0), "cap lai lan nua: khong lam gi");

  batDau("K24 - tat tieng 5 phut");
  doc(30, 5); doc(47, 2);
  batTatTieng(now);
  KIEM(dangTatTieng(now), "vua bam: dang tat tieng");
  now += 299000;
  KIEM(dangTatTieng(now), "sau 299 s: van tat tieng");
  now += 2000;
  KIEM(!dangTatTieng(now), "sau 301 s: tu het tat tieng");

  batDau("K24b - tat tieng tu huy khi phong nang hon");
  doc(30, 5); doc(47, 2);
  batTatTieng(now);
  docKhoi(true, 2);
  KIEM(mucPhong(0) == 3 && !dangTatTieng(now), "phong len cap 3 sau khi bam: hu tat tieng, coi keu lai");
  batDau("K24c - phong khac moi bao dong cung huy tat tieng");
  doc(30, 5); doc(47, 2);
  batTatTieng(now);
  baoDong[1] = true;
  KIEM(!dangTatTieng(now), "phong 2 moi bao dong: hu tat tieng");

  batDau("TB-05 - loi cam bien giu bao dong va ngat dien");
  doc(30, 5); doc(47, 2); doc(NAN, 3);
  KIEM(loiCamBien[0] && baoDong[0] && ngatDien[0], "loi khi dang bao dong: giu bao dong + ngat dien");

  printf("\nKet qua: %d dat, %d khong dat\n", dat, loi);
  return loi ? 1 : 0;
}
"""

with tempfile.TemporaryDirectory() as d:
    cpp = pathlib.Path(d) / "t.cpp"
    cpp.write_text(PRELUDE + cau_hinh + logic + TESTS, encoding="utf-8")
    exe = pathlib.Path(d) / "t"
    subprocess.run(["g++", "-std=c++17", "-Wall", "-o", str(exe), str(cpp)], check=True)
    sys.exit(subprocess.run([str(exe)]).returncode)
