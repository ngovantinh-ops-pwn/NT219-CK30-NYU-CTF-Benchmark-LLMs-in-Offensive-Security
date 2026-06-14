param(
    [ValidateSet("single_executor", "dcipher", "baseline")]
    [string]$Runner = "single_executor",
    [string]$RepoRoot = "D:\NT521-LTAT\llm_ctf_automation",
    [string]$Dataset = "D:\NT521-LTAT\NYU_CTF_Bench\test_dataset.json",
    [string]$Model = "cx/gpt-5.4",
    [string]$BaseUrl = "http://localhost:20128/v1",
    [string]$ExperimentName = "test_pwn_hard",
    [string]$ApiKey = "",
    [string]$BaselineConfig = "configs\baseline\base_config.yaml",
    [string]$ContainerImage = "ctfenv",
    [string]$Network = "ctfnet",
    [switch]$VerboseReasoning,
    [switch]$OverwriteExisting,
    [switch]$NoSkipExisting
)

& "$PSScriptRoot\\benchmark_pwn_test_group.ps1" `
    -Difficulty hard `
    -Runner $Runner `
    -RepoRoot $RepoRoot `
    -Dataset $Dataset `
    -Model $Model `
    -BaseUrl $BaseUrl `
    -ExperimentName $ExperimentName `
    -ApiKey $ApiKey `
    -BaselineConfig $BaselineConfig `
    -ContainerImage $ContainerImage `
    -Network $Network `
    -VerboseReasoning:$VerboseReasoning `
    -OverwriteExisting:$OverwriteExisting `
    -NoSkipExisting:$NoSkipExisting
