param(
  [Parameter(Mandatory=$true)][string]$TaskId,
  [Parameter(Mandatory=$true)][string]$TaskName,
  [Parameter(Mandatory=$true)][string]$Goal,
  [Parameter(Mandatory=$true)][string]$Boundary,
  [Parameter(Mandatory=$true)][string]$NextAction
)

$board = "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\02-任务与执行\TASK_STATE_BOARD.md"
$heartbeat = "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\02-任务与执行\EXECUTION_HEARTBEAT.md"
$now = Get-Date -Format "yyyy-MM-dd HH:mm"

if (-not (Test-Path $board)) { Write-Output "STATE_BOARD_MISSING"; exit 1 }
if (-not (Test-Path $heartbeat)) { Write-Output "HEARTBEAT_MISSING"; exit 1 }

Add-Content $heartbeat "- $now | $TaskId | entering executing | 目标：$Goal"
Add-Content $board "| $TaskId | $TaskName | $Goal | $Boundary | executing | $now | started via start-task.ps1 | $NextAction | 30m | 否 |"
Write-Output "TASK_STARTED:$TaskId"
