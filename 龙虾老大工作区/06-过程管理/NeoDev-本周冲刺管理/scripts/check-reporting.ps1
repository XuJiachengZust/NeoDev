param(
  [string]$StatePath = "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\02-任务与执行\TASK_STATE_BOARD.md",
  [string]$HeartbeatPath = "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\02-任务与执行\EXECUTION_HEARTBEAT.md"
)

$stateOk = $true
$heartbeatOk = $true

try {
  & "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\scripts\check-state.ps1" -Path $StatePath | Out-Host
  if ($LASTEXITCODE -ne 0) { $stateOk = $false }
} catch { $stateOk = $false }

try {
  & "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\scripts\check-heartbeat.ps1" -Path $HeartbeatPath | Out-Host
  if ($LASTEXITCODE -ne 0) { $heartbeatOk = $false }
} catch { $heartbeatOk = $false }

if ($stateOk -and $heartbeatOk) {
  Write-Output "REPORTING_ALLOWED"
} else {
  Write-Output "REPORTING_BLOCKED"
  exit 2
}
