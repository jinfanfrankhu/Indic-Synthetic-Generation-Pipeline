"""
One-off probe: do the judges *finely* discriminate Tamil quality, or do they
share blind spots?

The English-vs-Tamil control only tests the trivial case. Here we feed the same
Tamil QA item at graded quality tiers — clean -> one English word -> heavy
code-switch -> full English — and look at two things per judge:

  - does fluency grade *down* across the tiers (fine discrimination), and
  - do the judges *diverge* on the middle (code-switch) tiers?

All-high agreement on a code-switched item = shared blind spot (bad for an
ensemble, whose whole premise is decorrelated errors). A real spread = the
judges catch different things (good). No human labels needed: code-switching is
an objective, planted flaw (the project's own `bad-002` failure mode).

Run from the repo root:  python scripts/probe_judge_discrimination.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as `python scripts/probe_judge_discrimination.py` from the repo
# root (the script's own dir is on sys.path by default, not the repo root).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from syndata.compare import write_report
from syndata.data_structures import (
    GenerationConfig, QualityAxis, SeedItem, SyntheticItem, TaskFamily,
)
from syndata.judge import JudgeTarget, render_markdown, run_judge_panel

LANG = "ta"
SEED = SeedItem(
    id="seed-qa-001", task_family=TaskFamily.QA,
    prompt="What year did the first man walk on the moon?", expected="1969",
)

# Graded quality tiers for the *same* question. The clean tier is the actual
# DeepSeek output; the flawed tiers inject English content words (code-switch).
TIERS = [
    ("clean", "all Tamil (baseline)",
     "முதல் மனிதர் எந்த ஆண்டில் நிலவில் நடந்தார்?"),
    ("codeswitch-1", "one English word ('moon')",
     "முதல் மனிதர் எந்த ஆண்டில் moon-ல் நடந்தார்?"),
    ("codeswitch-heavy", "several English words",
     "First man எந்த year-ல் moon-ல் நடந்தார்?"),
    ("english", "full English (trivial control)",
     "What year did the first man walk on the moon?"),
]

JUDGES = [
    "sarvamai/sarvam-m",
    "mistralai/mistral-small-4-119b-2603",
    "z-ai/glm-5.1",
    "nvidia/nemotron-3-super-120b-a12b",
]


def _target(tier_id: str, label: str, prompt: str) -> JudgeTarget:
    cfg = GenerationConfig(
        seed_id=SEED.id, target_language=LANG,
        teacher_model="probe", prompt_template_name="probe",
    )
    item = SyntheticItem(
        id=f"ta-{tier_id}", seed_id=SEED.id, task_family=TaskFamily.QA,
        target_language=LANG, prompt=prompt, expected="1969",
        generation=cfg, generated_at=datetime.now(timezone.utc), raw_response=prompt,
    )
    return JudgeTarget(id=item.id, label=label, seed=SEED, item=item)


def main() -> None:
    targets = [_target(tid, label, prompt) for (tid, label, prompt) in TIERS]
    results = run_judge_panel(
        targets, JUDGES, max_tokens=1024, request_timeout=60, max_workers=2,
    )

    # Compact fluency gradient table to stdout (the discriminating axis).
    print("\nFLUENCY by tier (the discriminating axis):")
    header = f"{'tier':20s} | " + " | ".join(j.split('/')[-1][:14] for j in JUDGES)
    print(header)
    print("-" * len(header))
    for t in targets:
        cells = []
        for j in JUDGES:
            c = results[t.id][j]
            cells.append("ERR" if c.error else f"{c.score.scores[QualityAxis.FLUENCY]:.2f}")
        print(f"{t.id:20s} | " + " | ".join(f"{c:>14s}" for c in cells))

    out = write_report(render_markdown(targets, JUDGES, results), "docs/judge_probe_ta.md")
    print(f"\nFull report: {out}")


if __name__ == "__main__":
    main()
