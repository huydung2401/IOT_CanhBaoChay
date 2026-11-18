# Biên dịch lại firmware cho Wokwi trong VS Code (cần arduino-cli và core ESP32 3.x)
#   Cài 1 lần:
#     winget install ArduinoSA.CLI
#     arduino-cli config init
#     arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
#     arduino-cli core update-index
#     arduino-cli core install esp32:esp32
#     arduino-cli lib install PubSubClient "DHT sensor library for ESPx"
#   Chạy (từ thư mục gốc của project):
#     powershell -ExecutionPolicy Bypass -File wokwi\build_vscode.ps1
$goc = Split-Path -Parent $PSScriptRoot
foreach ($so in 1, 2) {
    $ra = Join-Path $PSScriptRoot ("esp0{0}\build" -f $so)
    Write-Host "== Bien dich esp0$so -> $ra"
    arduino-cli compile --fqbn esp32:esp32:esp32 `
        --build-property "compiler.cpp.extra_flags=-MMD -c -DSO_THIET_BI=$so" `
        --output-dir $ra (Join-Path $goc "canhbaochay_esp32")
    if ($LASTEXITCODE -ne 0) { throw "Bien dich esp0$so that bai" }
}
Write-Host "Xong. Trong VS Code: Wokwi: Start Simulator"
