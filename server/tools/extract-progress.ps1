# Live progress bar for the mmaps step of the client data extraction.
# Each extracted map tile (maps/*.map) becomes one navmesh tile (mmaps/*.mmtile).
#
#   powershell -ExecutionPolicy Bypass -File tools\extract-progress.ps1

$start = $null
$startDone = 0

while ($true) {
    $container = docker ps -q --filter "name=wow-tbc-extract"
    if (-not $container) {
        Write-Progress -Activity "mmaps" -Completed
        Write-Host "Extraction container is not running (finished, or not started)."
        break
    }

    $counts = docker exec $container sh -c 'echo $(ls /data/maps | grep -c "\.map$") $(ls /data/mmaps 2>/dev/null | grep -c "\.mmtile$")'
    $total, $done = $counts.Trim() -split '\s+' | ForEach-Object { [int]$_ }
    if ($total -eq 0) { Start-Sleep 5; continue }

    if (-not $start) { $start = Get-Date; $startDone = $done }
    $pct = [math]::Min(100, [math]::Round(100 * $done / $total, 1))

    $status = "$done / $total tiles ($pct%)"
    $elapsed = ((Get-Date) - $start).TotalSeconds
    if ($elapsed -gt 30 -and $done -gt $startDone) {
        $rate = ($done - $startDone) / $elapsed
        $eta = [TimeSpan]::FromSeconds(($total - $done) / $rate)
        $status += ("  ~{0:hh\:mm} left" -f $eta)
    }

    Write-Progress -Activity "Building mmaps (navmesh)" -Status $status -PercentComplete $pct
    Start-Sleep 10
}
