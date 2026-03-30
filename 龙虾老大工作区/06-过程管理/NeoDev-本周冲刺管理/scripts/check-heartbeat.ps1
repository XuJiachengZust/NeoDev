param(
  [string]$Path = "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\02-任务与执行\EXECUTION_HEARTBEAT.md",
  [int]$WarnMinutes = 30
)

if (-not (Test-Path $Path)) {
  Write-Output "HEARTBEAT_LOG_MISSING"
  exit 1
}

$lines = Get-Content $Path | Where-Object { $_ -match '^\-\s+\d{4}\-' }
if (-not $lines -or $lines.Count -eq 0) {
  Write-Output "HEARTBEAT_EMPTY"
  exit 1
}

$last = $lines[-1]
if ($last -match '^\-\s+([0-9\-:\s]+)\s+\|\s+([^|]+)\s+\|') {
  $ts = [datetime]::Parse($matches[1].Trim())
  $task = $matches[2].Trim()
  $delta = (New-TimeSpan -Start $ts -End (Get-Date)).TotalMinutes
  if ($delta -gt $WarnMinutes) {
    Write-Output "HEARTBEAT_STALE:$task:$([math]::Round($delta,1))m"
    exit 2
  } else {
    Write-Output "HEARTBEAT_OK:$task:$([math]::Round($delta,1))m"
  }
} else {
  Write-Output "HEARTBEAT_PARSE_FAILED"
  exit 1
}
