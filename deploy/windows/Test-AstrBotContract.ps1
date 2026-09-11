[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runtimeRoot = Join-Path $projectRoot "runtime\AstrBot"
$python = Join-Path $runtimeRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "AstrBot isolated runtime is missing: $python"
}

$sourcePaths = @(
    (Join-Path $projectRoot "packages\apeiria-core\src"),
    (Join-Path $projectRoot "packages\anime-party\src"),
    (Join-Path $projectRoot "packages\astrbot-plugin-apeiria"),
    $runtimeRoot
)
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $sourcePaths -join [IO.Path]::PathSeparator
    & $python (Join-Path $projectRoot "tests\compat\verify_astrbot_event_contract.py")
    if ($LASTEXITCODE -ne 0) {
        throw "AstrBot event contract verification failed."
    }
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
