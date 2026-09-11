[CmdletBinding()]
param(
    [string]$SettingsPath = (Join-Path $PSScriptRoot "..\napcat\apeiria.local.json")
)

$ErrorActionPreference = "Stop"
$failures = [System.Collections.Generic.List[string]]::new()

if (-not (Test-Path -LiteralPath $SettingsPath -PathType Leaf)) {
    $failures.Add("Missing local settings: $SettingsPath")
} else {
    try {
        $settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
        if ($settings.qq_account_id -notmatch '^\d{5,12}$') {
            $failures.Add("qq_account_id must be a numeric test QQ ID")
        }
        if ($settings.allowed_group_ids.Count -ne 1 -or $settings.allowed_group_ids[0] -notmatch '^\d+$') {
            $failures.Add("Exactly one numeric test group must be allowed initially")
        }
        if ($settings.admin_ids.Count -lt 1 -or ($settings.admin_ids | Where-Object { $_ -notmatch '^\d+$' })) {
            $failures.Add("At least one numeric administrator QQ ID is required")
        }
        if ($settings.astrbot.onebot_reverse_ws_host -ne '127.0.0.1') {
            $failures.Add("OneBot must bind to 127.0.0.1 for local deployment")
        }
        if ($settings.napcat.reverse_ws_url -ne 'ws://127.0.0.1:6199/ws') {
            $failures.Add("NapCat reverse WebSocket URL must remain local")
        }
    } catch {
        $failures.Add("Local settings are not valid JSON: $($_.Exception.Message)")
    }
}

foreach ($port in 6185, 6199) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener -and $listener.LocalAddress -notin @('127.0.0.1', '::1')) {
        $failures.Add("Port $port is listening outside the loopback interface")
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ -ErrorAction Continue }
    exit 1
}

Write-Host "Apeiria local QQ-link settings passed readiness checks."
