param(
    [ValidateSet("scan", "clean")]
    [string]$Mode = "scan",
    [string]$RepoPath = ".",
    [switch]$IncludePorts
)

$ErrorActionPreference = "Stop"

$resolvedRepo = (Resolve-Path -LiteralPath $RepoPath).Path
$repoLower = $resolvedRepo.ToLowerInvariant()
$agentCommandPattern = '(^|\s)(vite|vi|uvicorn|gradio|streamlit|flask|fastapi|jupyter|marimo|chainlit|npm|pnpm|bun|node|python|pythonw|uv|task)(\s|$|\.exe)'
$appCommandPattern = 'vite|uvicorn|gradio|streamlit|flask|fastapi|jupyter|marimo|chainlit|omnivoice|OmniVoiceTTS'
$agentPortSet = [System.Collections.Generic.HashSet[int]]::new()
@(3000, 3001, 4173, 5000, 5173, 7860, 7861, 8000, 8080, 8501, 8888) | ForEach-Object {
    [void]$agentPortSet.Add([int]$_)
}
$currentProcessId = [int]$PID
$parentProcessId = [int](Get-CimInstance Win32_Process -Filter "ProcessId=$currentProcessId").ParentProcessId

function Get-DevProcesses {
    $listeners = @{}
    Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $agentPortSet.Contains([int]$_.LocalPort) } |
        ForEach-Object { $listeners[[int]$_.OwningProcess] = $true }

    $all = Get-CimInstance Win32_Process |
        Where-Object {
            $commandLine = $_.CommandLine
            $name = $_.Name
            $processId = [int]$_.ProcessId
            if ($processId -eq $currentProcessId -or $processId -eq $parentProcessId) {
                return $false
            }
            if ($commandLine -and ($commandLine -match 'task\s+localps' -or $commandLine -match 'local-processes\.ps1')) {
                return $false
            }
            ($listeners.ContainsKey($processId)) -or
                ($commandLine -and (
                    $commandLine.ToLowerInvariant().Contains($repoLower) -or
                    $commandLine -match $appCommandPattern -or
                    $commandLine -match $agentCommandPattern
                )) -or
                ($name -match '^(vite|uvicorn|gradio|streamlit|flask|jupyter|marimo|chainlit)(\.exe)?$')
        } |
        Select-Object ProcessId, Name, CommandLine

    $all | Sort-Object ProcessId -Unique
}

function Get-RepoProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $commandLine = $_.CommandLine
            $name = $_.Name
            $commandLine -and
                $commandLine.ToLowerInvariant().Contains($repoLower) -and
                (($name -match '^(python|pythonw|uv|node|npm|pnpm|bun|task|vite|uvicorn|gradio|streamlit|flask|jupyter|marimo|chainlit)(\.exe)?$') -or
                    ($commandLine -match $appCommandPattern) -or
                    ($commandLine -match $agentCommandPattern))
        } |
        Select-Object ProcessId, Name, CommandLine
}

if ($Mode -eq "scan") {
    Write-Host "Repo: $resolvedRepo"
    Write-Host ""
    Write-Host "Likely agent/dev app processes:"
    $processes = Get-DevProcesses
    if ($processes) {
        $processes | Format-List
    } else {
        Write-Host "No likely agent/dev app processes found."
    }

    if ($IncludePorts) {
        Write-Host ""
        Write-Host "Listening ports:"
        $listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Sort-Object LocalPort |
            Select-Object LocalAddress, LocalPort, OwningProcess, @{
                Name = "ProcessName"
                Expression = { (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName }
            }
        if ($listeners) {
            $listeners | Format-Table -AutoSize
        } else {
            Write-Host "No listening TCP ports found."
        }
    }
    exit 0
}

$targets = Get-RepoProcesses
if (-not $targets) {
    Write-Host "No repo-local dev processes found."
    exit 0
}

Write-Host "Repo-local dev processes to stop:"
$targets | Format-List

foreach ($process in $targets) {
    Write-Host ("Stopping PID {0} {1}" -f $process.ProcessId, $process.Name)
    Stop-Process -Id $process.ProcessId -Force -ErrorAction Continue
}
