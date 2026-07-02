# Buttery weekend autonomous run (registered for 9 AM & 3 PM ET, Fri-Sun).
#
# Design: the WRAPPER owns reliability (deterministic scorer + branch + commit + a
# GUARANTEED email), and the headless agent owns judgment (audit, docs, summary). If
# the agent misbehaves, the quota work still happened and you still get an email.
#
# -Budget lets the integration test run the scorer as a no-op (0) without spending quota.
param([int]$Budget = 210)

$repo = 'C:\repos\Indic'
$py   = 'C:\Users\frank.hu\AppData\Local\miniconda3\python.exe'
Set-Location $repo

# conda's SSL_CERT_FILE often points at a missing cacert.pem; hand children a real one.
$env:SSL_CERT_FILE = (& $py -c "import certifi; print(certifi.where())")

$ts  = Get-Date -Format 'yyyy-MM-dd_HHmm'
$log = Join-Path $repo "tools\run_$ts.log"

# 0. Ensure we are on weekend-batch (preserve its history; never reset it).
& git show-ref --verify --quiet refs/heads/weekend-batch
if ($LASTEXITCODE -eq 0) { & git checkout weekend-batch | Out-Null }
else { & git checkout -b weekend-batch | Out-Null }

# 1. Deterministic quota work: bounded, resumable back-translation scoring.
$scorer = (& $py tools\score_backtranslation.py --per-run-budget $Budget --calls-per-minute 12 2>&1 | Out-String)

# 2. Agent: audit + document + summarize (does NOT score or commit).
$prompt = Get-Content -Raw (Join-Path $repo 'tools\weekend_operator_prompt.md')
try { $agent = (& claude -p $prompt 2>&1 | Out-String) }
catch { $agent = "AGENT INVOCATION FAILED:`n" + ($_ | Out-String) }

# 3. Commit whatever changed to the branch (deterministic; failure if nothing to commit is fine).
& git add -A 2>&1 | Out-Null
& git commit -m "weekend-batch: automated run $ts" 2>&1 | Out-Null
$head = (& git rev-parse --short HEAD)
$branch = (& git rev-parse --abbrev-ref HEAD)

# 4. GUARANTEED email of the whole run.
$body = @"
Buttery weekend run $ts
branch: $branch  commit: $head

=== scorer ===
$scorer

=== agent audit / summary ===
$agent
"@
$body | Out-File -FilePath $log -Encoding utf8
& $py (Join-Path $repo 'tools\send_email.py') --subject "Buttery weekend $ts" --body-file $log 2>&1 | Out-Null
