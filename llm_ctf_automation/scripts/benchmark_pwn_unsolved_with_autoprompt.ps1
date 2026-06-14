param(
    [ValidateSet("single_executor", "dcipher")]
    [string]$Runner = "single_executor",

    [string]$RepoRoot = "D:\NT521-LTAT\llm_ctf_automation",
    [string]$Dataset = "D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json",
    [string]$Model = "cx/gpt-5.4",
    [string]$BaseUrl = "http://localhost:20128/v1",
    [string]$ExperimentName = "",
    [switch]$OverwriteExisting,
    [switch]$NoSkipExisting
)

$ErrorActionPreference = "Stop"

function Get-UnsolvedBothChallenges {
    param(
        [string]$SingleLogRoot,
        [string]$DcipherLogRoot,
        [string]$DatasetPath
    )

    $code = @'
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

pat = re.compile(r'^(.*?)(?:-\d{12})?$')

def collect(root):
    by = defaultdict(list)
    root = Path(root)
    if not root.exists():
        return by
    for p in root.rglob("*.json"):
        if "-pwn-" not in p.stem:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        m = pat.match(p.stem)
        canon = m.group(1) if m else p.stem
        by[canon].append(bool(data.get("success")))
    return by

single = collect(sys.argv[1])
dcipher = collect(sys.argv[2])
dataset_path = Path(sys.argv[3])
dataset = json.loads(dataset_path.read_text(encoding="utf-8"))

single_unsolved = {k for k, v in single.items() if not any(v)}
dcipher_unsolved = {k for k, v in dcipher.items() if not any(v)}

def challenge_points(chal_name):
    info = dataset.get(chal_name, {})
    rel_path = info.get("path")
    if not rel_path:
        return 10**9
    challenge_json = dataset_path.parent / rel_path / "challenge.json"
    try:
        meta = json.loads(challenge_json.read_text(encoding="utf-8"))
    except Exception:
        return 10**9
    return int(meta.get("points", meta.get("initial", 10**9)))

ordered = sorted(single_unsolved & dcipher_unsolved, key=lambda name: (challenge_points(name), name))
for name in ordered:
    print(name)
'@

    $scriptFile = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -LiteralPath $scriptFile -Value $code -Encoding UTF8
        $names = & python $scriptFile $SingleLogRoot $DcipherLogRoot $DatasetPath
        return @($names | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    }
    finally {
        Remove-Item -LiteralPath $scriptFile -Force -ErrorAction SilentlyContinue
    }
}

$singleLogRoot = Join-Path $RepoRoot "logs_single_executor\Admin"
$dcipherLogRoot = Join-Path $RepoRoot "logs_dcipher\Admin"
$allChallenges = Get-UnsolvedBothChallenges -SingleLogRoot $singleLogRoot -DcipherLogRoot $dcipherLogRoot -DatasetPath $Dataset

if (-not $allChallenges -or $allChallenges.Count -eq 0) {
    Write-Host "Khong tim thay challenge pwn nao ma ca single_executor va dcipher deu chua solve." -ForegroundColor Yellow
    exit 0
}

if ([string]::IsNullOrWhiteSpace($ExperimentName)) {
    $ExperimentName = "test_pwn_unsolved_both_autoprompt"
}

$pythonCmd = "python"
$scriptName = if ($Runner -eq "dcipher") { "run_dcipher.py" } else { "run_single_executor.py" }

Write-Host "Repo root      : $RepoRoot"
Write-Host "Runner         : $Runner"
Write-Host "Dataset        : $Dataset"
Write-Host "Model          : $Model"
Write-Host "Base URL       : $BaseUrl"
Write-Host "Experiment name: $ExperimentName"
Write-Host "Autoprompt     : True"
Write-Host "Challenges     : $($allChallenges.Count)"
Write-Host ""
Write-Host "Danh sach challenge chua solve boi ca single_executor va dcipher:" -ForegroundColor Cyan
$allChallenges | ForEach-Object { Write-Host " - $_" }
Write-Host ""

Push-Location $RepoRoot
try {
    foreach ($challenge in $allChallenges) {
        Write-Host "============================================================"
        Write-Host "Challenge: $challenge"
        Write-Host "============================================================"
        Write-Host "Lua chon truoc khi chay:" -ForegroundColor Cyan
        Write-Host "  R = chay challenge nay"
        Write-Host "  S = bo qua va chuyen sang challenge ke tiep"
        Write-Host "  N = dung benchmark"

        $answer = (Read-Host "Chon [R/S/N]").Trim()
        $shouldRun = $false
        switch -Regex ($answer) {
            '^(?i)r(?:un)?$' {
                $shouldRun = $true
                Write-Host "Bat dau chay $challenge ..." -ForegroundColor Green
            }
            '^(?i)s(?:kip)?$' {
                Write-Host "Bo qua $challenge va chuyen sang challenge ke tiep." -ForegroundColor Yellow
            }
            '^(?i)n(?:o)?$' {
                Write-Host "Dung benchmark theo yeu cau cua ban." -ForegroundColor Yellow
                break
            }
            default {
                Write-Host "Khong nhan dang lua chon, mac dinh bo qua challenge nay." -ForegroundColor Yellow
            }
        }

        if (-not $shouldRun) {
            Write-Host ""
            continue
        }

        Write-Host "============================================================"
        Write-Host "Running $challenge"
        Write-Host "============================================================"

        $argsList = @(
            $scriptName,
            "--dataset", $Dataset,
            "--challenge", $challenge,
            "--openai-base-url", $BaseUrl,
            "--experiment-name", $ExperimentName,
            "--enable-autoprompt"
        )

        if ($Runner -eq "dcipher") {
            $argsList += @(
                "--planner-model", $Model,
                "--executor-model", $Model,
                "--autoprompter-model", $Model
            )
        } else {
            $argsList += @(
                "--executor-model", $Model,
                "--autoprompter-model", $Model
            )
        }

        if ($OverwriteExisting) {
            $argsList += "--overwrite-existing"
        } elseif (-not $NoSkipExisting) {
            $argsList += "--skip-existing"
        }

        & $pythonCmd @argsList

        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "Run failed at challenge: $challenge" -ForegroundColor Red
        }

        Write-Host ""
    }
}
finally {
    Pop-Location
}
