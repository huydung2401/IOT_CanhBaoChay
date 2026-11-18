# Xếp cửa sổ: dashboard nửa trái, VS Code esp01 góc phải trên, esp02 góc phải dưới.
# Mô phỏng Wokwi bị bóp tốc độ khi cửa sổ VS Code bị che kín hoặc thu nhỏ,
# nên cả hai cửa sổ simulator phải luôn còn hiện trên màn hình.
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class CuaSo {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int hh, bool r);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    public static List<KeyValuePair<IntPtr, string>> TatCa() {
        var ds = new List<KeyValuePair<IntPtr, string>>();
        EnumWindows((h, l) => {
            if (IsWindowVisible(h)) {
                var sb = new StringBuilder(512);
                GetWindowText(h, sb, 512);
                if (sb.Length > 0) ds.Add(new KeyValuePair<IntPtr, string>(h, sb.ToString()));
            }
            return true;
        }, IntPtr.Zero);
        return ds;
    }
}
"@
[CuaSo]::SetProcessDPIAware() | Out-Null
Add-Type -AssemblyName System.Windows.Forms
$wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$nuaW = [int]($wa.Width / 2)
$nuaH = [int]($wa.Height / 2)

function Tim($mauList) {
    foreach ($mau in $mauList) {
        $c = [CuaSo]::TatCa() | Where-Object { $_.Value -like $mau } | Select-Object -First 1
        if ($c) { return $c }
    }
    return $null
}
function Dat($ten, $mauList, $x, $y, $w, $h) {
    for ($i = 0; $i -lt 20; $i++) {            # chờ tối đa ~20 s cho cửa sổ xuất hiện
        $c = Tim $mauList
        if ($c) {
            [CuaSo]::ShowWindow($c.Key, 9) | Out-Null   # 9 = khôi phục nếu đang phóng to/thu nhỏ
            [CuaSo]::MoveWindow($c.Key, $x, $y, $w, $h, $true) | Out-Null
            Write-Host "  Da xep $ten : $($c.Value)"
            return
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "  Khong tim thay cua so $ten (bo qua)"
}

Dat "dashboard" @("*Bảng điều khiển*", "*Dashboard*", "*localhost:1880*") $wa.X $wa.Y $nuaW $wa.Height
Dat "esp01"     @("*esp01*Visual Studio Code*") ($wa.X + $nuaW) $wa.Y $nuaW $nuaH
Dat "esp02"     @("*esp02*Visual Studio Code*") ($wa.X + $nuaW) ($wa.Y + $nuaH) $nuaW $nuaH
