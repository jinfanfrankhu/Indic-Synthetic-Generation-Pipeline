# Scheduled regen of the translation family after the Gemini daily quota resets.
# Cleans the broken items, then re-drips translation with the corrected template.
# Reads GEMINI_API_KEY from the repo .env (CWD must be the repo).
$ErrorActionPreference = 'Stop'
$repo = 'C:\repos\Indic'
$py   = 'C:\Users\frank.hu\AppData\Local\miniconda3\python.exe'
Set-Location $repo
$ts  = Get-Date -Format 'yyyyMMddTHHmmss'
$log = Join-Path $repo "tools\regen_$ts.log"

"[$(Get-Date)] cleanup broken translation items" | Out-File -FilePath $log -Encoding utf8
& $py tools\clean_broken_translation.py *>> $log

"[$(Get-Date)] re-drip translation (per-combo 40, 12/min)" | Out-File -FilePath $log -Append -Encoding utf8
& $py -c "from syndata.cli import main; main()" generate-drip `
    --languages hi,ur,ta,ml --tasks translation --per-combo 40 `
    --teacher gemini:gemini-3.1-flash-lite --calls-per-minute 12 `
    --seeds data/seeds/seed_pool_20260629.json *>> $log

"[$(Get-Date)] done" | Out-File -FilePath $log -Append -Encoding utf8

# One-shot job: unregister self so it doesn't re-fire on later days.
try { Unregister-ScheduledTask -TaskName 'ButteryTranslationRegen' -Confirm:$false } catch {}
