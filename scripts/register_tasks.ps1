# Registers Windows Task Scheduler jobs (run PowerShell as your normal user, from the repo root).
#   .\scripts\register_tasks.ps1                 # full schedule (needs the 20K Odds API plan)
#   .\scripts\register_tasks.ps1 -FreePlan       # one cheap NBA pregame pull per day (fits 500 credits)
#   .\scripts\register_tasks.ps1 -Remove         # remove all MPM tasks
param([switch]$FreePlan, [switch]$Remove, [string]$InjuryFolder = "C:\MaverickPicks\injury_reports")
. "$PSScriptRoot\find_python.ps1"
$py   = Get-MpmPython
$repo = (Resolve-Path .).Path
$names = @()
function Add-MpmTask($name, $args_, $time, [int]$repeatMin = 0, [int]$durationHours = 0) {
    $action  = New-ScheduledTaskAction -Execute $py -Argument $args_ -WorkingDirectory $repo
    $trigger = New-ScheduledTaskTrigger -Daily -At $time
    if ($repeatMin -gt 0) {
        $rep = (New-ScheduledTaskTrigger -Once -At $time -RepetitionInterval (New-TimeSpan -Minutes $repeatMin) -RepetitionDuration (New-TimeSpan -Hours $durationHours)).Repetition
        $trigger.Repetition = $rep
    }
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
    Register-ScheduledTask -TaskName "MPM $name" -TaskPath "\MaverickPicks\" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "registered: MPM $name ($time)"
}
if ($Remove) { Get-ScheduledTask -TaskPath "\MaverickPicks\" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false; Write-Host "removed"; exit }

if ($FreePlan) {
    # ~3 credits/day = ~90/month (main markets only)
    Add-MpmTask "NBA odds pregame" "-m mpm.oddsapi --league NBA --purpose pregame --no-team-totals" "6:15PM"
} else {
    foreach ($lg in "NBA","NHL") {
        Add-MpmTask "$lg odds open"    "-m mpm.oddsapi --league $lg --purpose open --no-team-totals" "10:30AM"     # 3 credits
        Add-MpmTask "$lg odds pregame" "-m mpm.oddsapi --league $lg --purpose pregame"             "6:00PM"      # 3 + 1/game
        Add-MpmTask "$lg odds close"   "-m mpm.oddsapi --league $lg --close-window 15"             "12:00PM" 10 12   # 4/game, once per game
    }
}
foreach ($t in "1:45PM","5:45PM","6:45PM") {
    Add-MpmTask "NBA injury report $($t.Replace(':',''))" "-m mpm.injuries --fetch `"$InjuryFolder`"" $t
}
Write-Host "Done. See Task Scheduler > Task Scheduler Library > MaverickPicks."
