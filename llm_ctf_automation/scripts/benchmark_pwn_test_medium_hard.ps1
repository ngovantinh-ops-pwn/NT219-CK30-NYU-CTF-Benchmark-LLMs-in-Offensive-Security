param(
    [ValidateSet("single_executor", "dcipher", "baseline")]
    [string]$Runner = "single_executor",

    [string]$RepoRoot = "D:\NT521-LTAT\llm_ctf_automation",
    [string]$Dataset = "D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json",
    [string]$Model = "cx/gpt-5.4",
    [string]$BaseUrl = "http://localhost:20128/v1",
    [string]$ExperimentName = "test_pwn_medium_hard",
    [string]$ApiKey = "",
    [string]$BaselineConfig = "configs\baseline\base_config.yaml",
    [string]$ContainerImage = "ctfenv",
    [string]$Network = "ctfnet",

    [switch]$VerboseReasoning,
    [switch]$OverwriteExisting,
    [switch]$NoSkipExisting
)

$ErrorActionPreference = "Stop"

$mediumChallenges = @(
    "2023f-pwn-virtualization_pwn",
    "2020q-pwn-grid",
    "2020q-pwn-thebardsfail",
    "2019f-pwn-arevenge",
    "2019q-pwn-traveller",
    "2020f-pwn-darkunion1",
    "2020q-pwn-pwnvoltex",
    "2019q-pwn-popping_caps",
    "2020q-pwn-blox2"
)

$hardChallenges = @(
    "2019q-pwn-popping_caps_2",
    "2020q-pwn-feather",
    "2018f-pwn-es1337",
    "2019q-pwn-pop_goes_the_printer"
)

$allChallenges = @($mediumChallenges + $hardChallenges)

$pythonCmd = "python"
$scriptName = switch ($Runner) {
    "dcipher" { "run_dcipher.py" }
    "baseline" { "run_baseline.py" }
    default { "run_single_executor.py" }
}

Write-Host "Repo root      : $RepoRoot"
Write-Host "Runner         : $Runner"
Write-Host "Dataset        : $Dataset"
Write-Host "Model          : $Model"
Write-Host "Base URL       : $BaseUrl"
Write-Host "Experiment name: $ExperimentName"
if ($Runner -eq "baseline") {
    Write-Host "Baseline config: $BaselineConfig"
    Write-Host "Container image: $ContainerImage"
    Write-Host "Network        : $Network"
}
Write-Host "Verbose reason : $($VerboseReasoning.IsPresent)"
Write-Host "Challenges     : $($allChallenges.Count)"
Write-Host ""

Push-Location $RepoRoot
try {
    foreach ($challenge in $allChallenges) {
        Write-Host "============================================================"
        Write-Host "Running $challenge"
        Write-Host "============================================================"

        if ($Runner -eq "baseline") {
            $argsList = @(
                $scriptName,
                "-c", $BaselineConfig,
                "--dataset", $Dataset,
                "--challenge", $challenge,
                "--backend", "openai",
                "--model", $Model,
                "--api-endpoint", $BaseUrl,
                "--container-image", $ContainerImage,
                "--network", $Network,
                "--name", $ExperimentName
            )
            if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
                $argsList += @("--api-key", $ApiKey)
            }
            if ($OverwriteExisting) {
            } elseif (-not $NoSkipExisting) {
                $argsList += "--skip-exist"
            }
        } else {
            $argsList = @(
                $scriptName,
                "--dataset", $Dataset,
                "--challenge", $challenge,
                "--openai-base-url", $BaseUrl,
                "--experiment-name", $ExperimentName
            )
        }

        if ($Runner -eq "dcipher") {
            $argsList += @(
                "--planner-model", $Model,
                "--executor-model", $Model,
                "--autoprompter-model", $Model
            )
        } elseif ($Runner -eq "single_executor") {
            $argsList += @(
                "--executor-model", $Model,
                "--autoprompter-model", $Model
            )
        }

        if ($VerboseReasoning -and $Runner -ne "baseline") {
            $argsList += "--verbose-reasoning"
        }
        if ($Runner -ne "baseline" -and $OverwriteExisting) {
            $argsList += "--overwrite-existing"
        } elseif ($Runner -ne "baseline" -and -not $NoSkipExisting) {
            $argsList += "--skip-existing"
        }

        & $pythonCmd @argsList
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "Run failed at challenge: $challenge" -ForegroundColor Red
            Write-Host "Stopping benchmark script." -ForegroundColor Red
            exit $LASTEXITCODE
        }

        Write-Host ""
    }

    Write-Host "All requested benchmark runs finished." -ForegroundColor Green
}
finally {
    Pop-Location
}
