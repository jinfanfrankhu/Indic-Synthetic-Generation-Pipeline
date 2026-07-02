# Buttery weekend autonomous run (registered 9 AM & 3 PM ET, Fri-Sun).
#
# The WRAPPER owns reliability (deterministic scorers + audit + commit + a GUARANTEED
# email); the headless agent is a read-only interpreter that adds judgement to the
# summary. A detached `claude -p` can Read but not execute/write, so all work is done
# here as plain commands — the agent only reads the results and comments.
#
# -JudgeBudget caps judge attempts this run; -SkipAgent skips the claude -p step (tests).
param([int]$JudgeBudget = 450, [switch]$SkipAgent, [switch]$SkipBT)

$repo = 'C:\repos\Indic'
$py   = 'C:\Users\frank.hu\AppData\Local\miniconda3\python.exe'
Set-Location $repo
$env:SSL_CERT_FILE = (& $py -c "import certifi; print(certifi.where())")
$ts  = Get-Date -Format 'yyyy-MM-dd_HHmm'
$log = Join-Path $repo "tools\run_$ts.log"

# 0. weekend-batch branch (preserve history; never reset).
& git show-ref --verify --quiet refs/heads/weekend-batch
if ($LASTEXITCODE -eq 0) { & git checkout weekend-batch | Out-Null } else { & git checkout -b weekend-batch | Out-Null }

# 1. Back-translation (local NLLB, unlimited). No-op fast if nothing new; --include-translation
#    picks up items from Friday's 3:15 AM translation regen.
if ($SkipBT) { $bt = "(back-translation skipped)" }
else { $bt = (& $py tools\score_backtranslation.py --include-translation 2>&1 | Out-String) }

# 2. Judge ensemble drip (OpenRouter free, resumable, budget/congestion-aware).
$judge = (& $py tools\score_judge.py --per-run-budget $JudgeBudget --include-translation 2>&1 | Out-String)

# 3. Deterministic audit (structural + back-translation + judge distributions).
$audit = (& $py tools\audit.py 2>&1 | Out-String)

# 4. Persist for the read-only agent + append the durable log.
"BACK-TRANSLATION:`n$bt`n`nJUDGE:`n$judge`n`nAUDIT:`n$audit" |
    Out-File -FilePath (Join-Path $repo 'tools\latest_audit.txt') -Encoding utf8
"`n## $ts`n``````n$bt$judge$audit``````" |
    Out-File -FilePath (Join-Path $repo 'tools\weekend_log.md') -Append -Encoding utf8

# 5. Agent: READ-ONLY interpretation/summary (adds judgement; writes nothing).
$agent = ""
if (-not $SkipAgent) {
    $prompt = Get-Content -Raw (Join-Path $repo 'tools\weekend_operator_prompt.md')
    try { $agent = (& claude -p $prompt 2>&1 | Out-String) }
    catch { $agent = "AGENT INVOCATION FAILED:`n" + ($_ | Out-String) }
}

# 6. Commit doc progress (weekend_log.md, any hand METHODOLOGY edits).
& git add -A 2>&1 | Out-Null
& git commit -m "weekend-batch: automated run $ts" 2>&1 | Out-Null
$head = (& git rev-parse --short HEAD); $branch = (& git rev-parse --abbrev-ref HEAD)

# 7. GUARANTEED email.
$body = @"
Buttery weekend run $ts
branch: $branch  commit: $head

=== back-translation ===
$bt
=== judge ensemble ===
$judge
=== audit ===
$audit
=== agent interpretation ===
$agent
"@
$body | Out-File -FilePath $log -Encoding utf8
& $py (Join-Path $repo 'tools\send_email.py') --subject "Buttery weekend $ts" --body-file $log 2>&1 | Out-Null
