param(
  [string]$Path = "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\02-任务与执行\TASK_STATE_BOARD.md"
)

if (-not (Test-Path $Path)) {
  Write-Output "STATE_BOARD_MISSING"
  exit 1
}

$content = Get-Content $Path -Raw
$lines = $content -split "`r?`n" | Where-Object { $_ -match '^\|\s*[^-].*\|$' }
$rows = $lines | Select-Object -Skip 2
$issues = @()

foreach ($row in $rows) {
  $cols = $row.Trim('|').Split('|').ForEach({ $_.Trim() })
  if ($cols.Count -lt 10) { continue }
  $taskId = $cols[0]
  $goal = $cols[2]
  $boundary = $cols[3]
  $state = $cols[4]
  $evidence = $cols[6]
  $next = $cols[7]
  if ([string]::IsNullOrWhiteSpace($goal) -or [string]::IsNullOrWhiteSpace($boundary)) {
    $issues += "MISSING_GOAL_OR_BOUNDARY:$taskId"
  }
  if ($state -eq 'executing') {
    if ([string]::IsNullOrWhiteSpace($evidence)) { $issues += "EXECUTING_WITHOUT_EVIDENCE:$taskId" }
    if ([string]::IsNullOrWhiteSpace($next)) { $issues += "EXECUTING_WITHOUT_NEXT_ACTION:$taskId" }
  }
}

if ($issues.Count -eq 0) {
  Write-Output "STATE_OK"
} else {
  $issues | ForEach-Object { Write-Output $_ }
  exit 2
}
