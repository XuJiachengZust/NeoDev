param()

$script = "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\scripts\check-reporting.ps1"
if (-not (Test-Path $script)) {
  Write-Output "REPORTING_CHECK_MISSING"
  exit 1
}

& $script
if ($LASTEXITCODE -ne 0) {
  Write-Output "DO_NOT_REPORT_PROGRESS"
  exit 2
}

Write-Output "REPORTING_ALLOWED_USE_EVIDENCE_TEMPLATE"
