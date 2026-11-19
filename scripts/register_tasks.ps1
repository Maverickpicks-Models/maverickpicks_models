# Registers Windows Task Scheduler jobs (run PowerShell as your normal user, from the repo root).
#   .\scripts\register_tasks.ps1                 # full schedule (needs the 20K Odds API plan)
#   .\scripts\register_tasks.ps1 -FreePlan       # one cheap NBA pregame pull per day (fits 500 credits)
#   .\scripts\register_tasks.ps1 -Remove         # remove all MPM tasks
#   .\scripts\register_tasks.ps1 -MoneyPuck      # also the daily MoneyPuck download (get MoneyPuck's permission first:
#                                                 #  moneypuck.com/data.htm allows non-commercial use only without it)
param([switch]$FreePlan, [switch]$Remove, [switch]$MoneyPuck, [string]$InjuryFolder = "C:\MaverickPicks\injury_reports",
      [string]$MoneyPuckFolder = "C:\MaverickPicks\moneypuck")
. "$PSScriptRoot\find_python.ps1"
$py   = Get-MpmPython
$repo = (Resolve-Path .).Path
$names = @()
function Add-MpmTask($name, $args_, $time, [int]$repeatMin = 0, [int]$durationHours = 0) {
    # every job goes through mpm.run, which logs output and errors to C:\MaverickPicks\logs\<date>.log
    $action  = New-ScheduledTaskAction -Execute $py -Argument ($args_ -replace '^-m mpm\.', '-m mpm.run ') -WorkingDirectory $repo
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
    # staggered so no two jobs call TheOddsAPI in the same minute (the close checks run on :00/:10/:20...)
    $open = @{ NBA = "10:32AM"; NHL = "10:34AM" }; $pre = @{ NBA = "6:02PM"; NHL = "6:04PM" }
    foreach ($lg in "NBA","NHL") {
        Add-MpmTask "$lg odds open"    "-m mpm.oddsapi --league $lg --purpose open --no-team-totals" $open[$lg]   # 3 credits
        Add-MpmTask "$lg odds pregame" "-m mpm.oddsapi --league $lg --purpose pregame"             $pre[$lg]    # 3 + 1/game
        Add-MpmTask "$lg odds close"   "-m mpm.oddsapi --league $lg --close-window 15"             "12:00PM" 10 12   # 4/game, once per game
    }
    # stale-line scan: main markets from all 10 books every 10 min, 4 PM to 11 PM (3 credits a pull,
    # ~130/night for both leagues). Each pull is checked for Novig prices lagging Pinnacle (mpm.stale).
    Add-MpmTask "NBA odds scan" "-m mpm.oddsapi --league NBA --purpose scan --no-team-totals" "4:05PM" 10 7
    Add-MpmTask "NHL odds scan" "-m mpm.oddsapi --league NHL --purpose scan --no-team-totals" "4:07PM" 10 7
}
# injury report: check every 15 minutes, 11:50 AM to midnight (free). A new report is loaded once and
# checked against tonight's watch list (mpm.watch), which pops up an alert when a player in a game we bet changes.
foreach ($old in "145PM","545PM","645PM") { Unregister-ScheduledTask -TaskName "MPM NBA injury report $old" -TaskPath "\MaverickPicks\" -Confirm:$false -ErrorAction SilentlyContinue }
Add-MpmTask "NBA injury report" "-m mpm.injuries --fetch `"$InjuryFolder`"" "11:50AM" 15 12
if ($MoneyPuck) {
    Add-MpmTask "NHL MoneyPuck daily" "-m mpm.moneypuck --fetch `"$MoneyPuckFolder`"" "9:30AM"     # free, 2 small CSVs
}
Write-Host "Done. See Task Scheduler > Task Scheduler Library > MaverickPicks."
