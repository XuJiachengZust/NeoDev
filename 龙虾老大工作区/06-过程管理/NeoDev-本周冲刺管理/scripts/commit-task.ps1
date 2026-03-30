param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [Parameter(Mandatory=$true)][string]$Message
)

$rules = "C:\Users\AH\Desktop\龙虾老大工作区\NeoDev-本周冲刺管理\03-审核与问题\PRE_COMMIT_RULES.md"
if (-not (Test-Path $rules)) {
  Write-Output "PRE_COMMIT_RULES_MISSING"
  exit 1
}

$status = git -C $Repo diff --name-only --cached
if (-not $status) {
  Write-Output "NO_STAGED_FILES"
  exit 1
}

$blockedPatterns = @('web/dist/','web/node_modules/','__pycache__/','.cursor/plans/','.claude/','docker/images/','.tar','bash.exe.stackdump')
$violations = @()
foreach ($line in $status) {
  foreach ($pat in $blockedPatterns) {
    if ($line -like "*$pat*" -or $line -like "*$pat") {
      $violations += $line
    }
  }
}

if ($violations.Count -gt 0) {
  $violations | ForEach-Object { Write-Output "BLOCKED_STAGED_FILE:$_" }
  exit 2
}

git -C $Repo commit -m $Message
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "COMMIT_DONE"
