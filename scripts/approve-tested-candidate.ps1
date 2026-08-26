[CmdletBinding()]
param(
    [ValidateRange(1, [int]::MaxValue)]
    [int]$PullRequest,

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Require-Command {
    param([Parameter(Mandatory)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Invoke-GhJson {
    param([Parameter(Mandatory)][string[]]$Arguments)

    $text = & gh @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gh command failed: gh $($Arguments -join ' ')"
    }
    return (($text -join "`n") | ConvertFrom-Json)
}

function Invoke-Gh {
    param([Parameter(Mandatory)][string[]]$Arguments)

    & gh @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gh command failed: gh $($Arguments -join ' ')"
    }
}

Require-Command gh
Require-Command adb

Invoke-Gh @('auth', 'status')
$repository = (& gh repo view --json nameWithOwner --jq '.nameWithOwner').Trim()
if ($LASTEXITCODE -ne 0 -or -not $repository) {
    throw 'Could not resolve the GitHub repository from this checkout.'
}

if (-not $PSBoundParameters.ContainsKey('PullRequest')) {
    $resolvedPr = (& gh pr view --json number --jq '.number').Trim()
    if ($LASTEXITCODE -ne 0 -or $resolvedPr -notmatch '^[1-9][0-9]*$') {
        throw 'Could not infer a pull request from the current branch. Pass -PullRequest NUMBER.'
    }
    $PullRequest = [int]$resolvedPr
}

$pull = Invoke-GhJson @('api', "repos/$repository/pulls/$PullRequest")
if ($pull.state -ne 'open' -or $pull.base.ref -ne 'main') {
    throw "PR #$PullRequest must be open and target main."
}
if ($pull.head.repo.full_name -ne $repository) {
    throw "PR #$PullRequest must originate from the same repository."
}
$headSha = [string]$pull.head.sha
if ($headSha -notmatch '^[0-9a-f]{40}$') {
    throw 'The PR head is not a full Git commit SHA.'
}

$runs = Invoke-GhJson @(
    'api', '--method', 'GET',
    "repos/$repository/actions/workflows/kernel-candidate.yml/runs?event=pull_request&per_page=100"
)
$candidateRuns = @(
    $runs.workflow_runs |
        Where-Object {
            $_.conclusion -eq 'success' -and
            $_.head_sha -eq $headSha -and
            @($_.pull_requests | Where-Object { $_.number -eq $PullRequest }).Count -gt 0
        } |
        Sort-Object run_number
)
if ($candidateRuns.Count -eq 0) {
    throw "No successful candidate build exists for the current head of PR #$PullRequest."
}
$candidateRun = $candidateRuns[-1]
$runId = [string]$candidateRun.id

$artifacts = Invoke-GhJson @('api', "repos/$repository/actions/runs/$runId/artifacts?per_page=100")
$packageArtifacts = @(
    $artifacts.artifacts | Where-Object {
        -not $_.expired -and
        $_.name -like 'CANDIDATE_SukiSU_kebab_extended-full-hide_*'
    }
)
$metadataArtifacts = @(
    $artifacts.artifacts | Where-Object {
        -not $_.expired -and $_.name -eq 'CANDIDATE_kernel-lineage-23.2_metadata'
    }
)
if ($packageArtifacts.Count -ne 1 -or $metadataArtifacts.Count -ne 1) {
    throw 'Expected exactly one current-config package and one metadata artifact.'
}

$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$tempDirectory = Join-Path $tempRoot "kernel-candidate-approval-$([guid]::NewGuid().ToString('N'))"
[System.IO.Directory]::CreateDirectory($tempDirectory) | Out-Null

try {
    $packageDirectory = Join-Path $tempDirectory 'package'
    $metadataDirectory = Join-Path $tempDirectory 'metadata'
    [System.IO.Directory]::CreateDirectory($packageDirectory) | Out-Null
    [System.IO.Directory]::CreateDirectory($metadataDirectory) | Out-Null

    Invoke-Gh @(
        'run', 'download', $runId, '--repo', $repository,
        '--name', [string]$packageArtifacts[0].name, '--dir', $packageDirectory
    )
    Invoke-Gh @(
        'run', 'download', $runId, '--repo', $repository,
        '--name', [string]$metadataArtifacts[0].name, '--dir', $metadataDirectory
    )

    $packages = @(Get-ChildItem -LiteralPath $packageDirectory -Recurse -File -Filter '*.zip')
    $metadataFiles = @(Get-ChildItem -LiteralPath $metadataDirectory -Recurse -File -Filter 'candidate.json')
    if ($packages.Count -ne 1 -or $metadataFiles.Count -ne 1) {
        throw 'Downloaded artifacts do not contain exactly one candidate ZIP and candidate.json.'
    }

    $metadata = Get-Content -LiteralPath $metadataFiles[0].FullName -Raw | ConvertFrom-Json
    $buildFingerprint = [string]$metadata.build_fingerprint
    if (
        $metadata.pr -ne $PullRequest -or
        $metadata.head_sha -ne $headSha -or
        $buildFingerprint -notmatch '^[0-9a-f]{64}$'
    ) {
        throw 'Candidate metadata does not match the selected PR head.'
    }

    $packageSha256 = (Get-FileHash -LiteralPath $packages[0].FullName -Algorithm SHA256).Hash.ToLowerInvariant()

    $deviceState = (& adb get-state 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or $deviceState -ne 'device') {
        throw 'ADB does not report exactly one authorized device in the device state.'
    }
    $romBuildFingerprint = (& adb shell getprop ro.build.fingerprint).Trim()
    if (
        $LASTEXITCODE -ne 0 -or
        $romBuildFingerprint.Length -lt 10 -or
        $romBuildFingerprint.Length -gt 512 -or
        $romBuildFingerprint.Contains("`n")
    ) {
        throw 'Could not read a valid ROM build fingerprint from the connected phone.'
    }

    Write-Host ''
    Write-Host "Repository:        $repository"
    Write-Host "Candidate PR:      #$PullRequest"
    Write-Host "PR head:           $headSha"
    Write-Host "Candidate run:     $runId"
    Write-Host "Build fingerprint: $buildFingerprint"
    Write-Host "Package SHA-256:   $packageSha256"
    Write-Host "ROM fingerprint:   $romBuildFingerprint"
    Write-Host ''

    if ($DryRun) {
        Write-Host 'Dry run complete; no approval was submitted.'
        return
    }

    $confirmation = Read-Host 'Type APPROVE only if this exact package passed the complete phone test'
    if ($confirmation -cne 'APPROVE') {
        throw 'Approval cancelled.'
    }

    Invoke-Gh @(
        'workflow', 'run', 'approve-kernel-candidate.yml',
        '--repo', $repository,
        '--ref', 'main',
        '--field', "pr_number=$PullRequest",
        '--field', "build_fingerprint=$buildFingerprint",
        '--field', "package_sha256=$packageSha256",
        '--field', "rom_build_fingerprint=$romBuildFingerprint"
    )

    Write-Host 'Approval workflow submitted. GitHub will independently verify every collected value.'
}
finally {
    $resolvedTemp = [System.IO.Path]::GetFullPath($tempDirectory)
    if (
        $resolvedTemp.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
        [System.IO.Path]::GetFileName($resolvedTemp).StartsWith(
            'kernel-candidate-approval-',
            [System.StringComparison]::Ordinal
        )
    ) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
