"""Creative seed authoring — broadens topic coverage beyond the mined-out basics.

Rotates each task family across diverse sub-domains, carries an explicit NEGATIVE
list of over-used topics to steer away from, and leans into culturally-grounded
Indic content (per DESIGN: bottom-up/reverse-instruction for culturally-grounded
tasks). Reuses the validated `_accept` pre-filters + dedup + id allocation from
syndata.bootstrap so nothing bypasses the quality gate.

Output: data/seeds/bootstrapped_<ts>.json  (then hand-review + drip, same as usual)
"""
from __future__ import annotations
import glob, json, os, sys
from datetime import datetime

from syndata.bootstrap import _accept, _normalize, parse_seed_array, BootstrapResult
from syndata.client import build_client
from syndata.data_structures import TaskFamily

TEACHER = os.environ.get("TEACHER", "claude-cli:sonnet")
PER_FAMILY = int(os.environ.get("PER_FAMILY", "20"))
PER_CALL = 5

SCHEMA = ('Output ONLY a JSON array (no fences, no commentary). Each object: '
          '{"prompt": str, "expected": str|null, "labels": [str]|null, '
          '"metadata": {"domain": str, "difficulty": str}}. Write in ENGLISH only. '
          'Avoid idioms/puns/wordplay that will not survive translation into Hindi, '
          'Urdu, Tamil, and Malayalam.')

# Per-family: rules + a NEGATIVE list + a rotation of creative angles.
FAMILIES = {
    TaskFamily.QA: {
        "rules": ('Each: a specific factual question in "prompt" and its short, '
                  'unambiguous answer in "expected" (a word/name/number/year, not a '
                  'sentence). VERIFY every answer is correct. Prefer stable, '
                  'well-established facts.'),
        "avoid": ('capital cities, chromosome counts, "largest/smallest ocean/planet/'
                  'state/country", boiling point of water, atomic numbers of common '
                  'elements, basic multiplication or square/cube roots, "which year '
                  'did WWI/WWII end", "who was the first President/Prime Minister".'),
        "angles": [
            "Indian classical arts, music, dance forms, and their regional origins",
            "Indian festivals, cuisine, and their states/regions of origin",
            "world and Indian geography beyond capitals — rivers, mountain ranges, deserts, biodiversity hotspots",
            "science concepts and natural phenomena (how/why questions with a short factual answer)",
            "Indian history — specific dynasties, movements, monuments, reformers",
            "space, technology, and modern institutions (ISRO missions, scientific units, inventions)",
            "world literature, cinema, and sports (stable, well-established facts)",
        ],
    },
    TaskFamily.REASONING: {
        "rules": ('Each: a multi-step problem in "prompt" ending with "Show your '
                  'reasoning step by step", and the correct final answer in '
                  '"expected". SOLVE it yourself and double-check — a wrong answer '
                  'corrupts every language.'),
        "avoid": ('simple/compound interest, pipes filling/draining a tank, '
                  'milk-and-water replacement, two trains/buses moving toward each '
                  'other, profit-percentage on buying/selling goods, "N workers '
                  'finish a job in D days". These are over-used — do NOT generate them.'),
        "angles": [
            "logic-grid / deductive puzzles (people, days, houses, professions with 3-4 interlocking clues)",
            "combinatorics and probability with varied real setups (committees, arrangements, cards, dice)",
            "geometry and mensuration in real scenarios (fields, tiles, tanks — areas, perimeters, angles)",
            "number theory and integer sequences with non-obvious patterns",
            "calendar, clock, and time-zone reasoning",
            "real-world multi-step planning (scheduling, unit-conversion chains, resource allocation)",
        ],
    },
    TaskFamily.TRANSLATION: {
        "rules": ('Each: a short, natural English sentence to translate in "prompt"; '
                  'leave "expected" as null. Vary register (formal, casual, literary, '
                  'instructional, emotional) and sentence type (statement, question, '
                  'exclamation, conditional).'),
        "avoid": ('"good morning / how is your family", "turn right at X and Y is on '
                  'your left", "the doctor advised rest/medicine", "the train to X '
                  'departs from platform N". Do NOT generate greetings, directions, '
                  'or doctor/medicine sentences.'),
        "angles": [
            "technology, science, and the internet in everyday life",
            "agriculture, weather, and the environment",
            "education, careers, and personal goals",
            "culture, festivals, and food (described, not just named)",
            "news-headline and public-announcement style sentences",
            "emotional and reflective sentences (hope, gratitude, worry, encouragement)",
        ],
    },
    TaskFamily.CLASSIFICATION: {
        "rules": ('Each: text to classify in "prompt", a "labels" array of >=2 '
                  'candidate labels, and the correct one in "expected". HARD RULES: '
                  '(1) "expected" MUST be exactly one of "labels"; (2) the "prompt" '
                  'MUST list the candidate labels inline (e.g. "... Options: a, b, c."). '
                  'Avoid sarcasm/irony (ambiguous after translation).'),
        "avoid": ('do not make every seed simple positive/negative sentiment or '
                  'basic news-topic labelling — vary the classification SCHEME.'),
        "angles": [
            "emotion classification (joy, anger, fear, sadness, surprise)",
            "intent classification (question, request, complaint, compliment, suggestion)",
            "formality/register classification (formal vs informal)",
            "urgency classification (urgent vs routine) of short messages",
            "stance classification (supports, opposes, neutral) on an everyday topic",
            "domain/topic classification with unusual category sets (agriculture, health, technology, sports, arts)",
        ],
    },
    TaskFamily.SUMMARIZATION: {
        "rules": ('Each: a self-contained factual passage of 3-5 sentences in '
                  '"prompt", and a faithful ONE-sentence reference summary in '
                  '"expected" that introduces no new facts.'),
        "avoid": ('vary the source domain — do not make them all about the same topic.'),
        "angles": [
            "a science discovery or natural phenomenon",
            "a historical event or figure (Indian or world)",
            "a how-something-works / process explainer",
            "an economic, social, or public-policy phenomenon",
            "an environmental or agricultural topic",
            "a cultural practice, art form, or festival",
        ],
    },
    TaskFamily.INSTRUCTION: {
        "rules": ('Each: a self-contained, open-ended instruction in "prompt"; leave '
                  '"expected" as null. Vary the TYPE of task.'),
        "avoid": ('do not repeat the same instruction verb — vary widely.'),
        "angles": [
            "explain a concept simply to a beginner",
            "write a short creative piece (a note, a description, a short dialogue)",
            "compare two things and lay out the trade-offs",
            "give a clear step-by-step how-to",
            "offer practical advice for a real-life situation",
            "analyze the pros and cons of a decision or plan",
        ],
    },
}


def build_pool():
    seen, pool = set(), []
    for f in sorted(glob.glob("data/seeds/*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for s in (d["seeds"] if isinstance(d, dict) else d):
            if "[mock" in (s.get("prompt") or ""): continue
            if s["id"] in seen: continue
            seen.add(s["id"]); pool.append(s)
    return pool


def main():
    pool = build_pool()
    pool_norm = {_normalize(s["prompt"]) for s in pool}
    taken = {s["id"] for s in pool}
    client = build_client(TEACHER)
    out_seeds = []

    for task, cfg in FAMILIES.items():
        result = BootstrapResult(task=task, seeds=[], requested=PER_FAMILY)
        seen_local = set()
        angles = cfg["angles"]
        # rotate angles until PER_FAMILY collected or budget spent
        max_calls = len(angles) * 3
        calls = 0
        ai = 0
        while len(result.seeds) < PER_FAMILY and calls < max_calls:
            angle = angles[ai % len(angles)]; ai += 1; calls += 1
            system = (f"You author seed tasks for an instruction-tuning dataset for "
                      f"low-resource Indic languages. Generate NEW, DIVERSE English "
                      f"'{task.value}' seeds. {cfg['rules']}\n"
                      f"AVOID these over-used topics: {cfg['avoid']}\n"
                      f"Prefer universal or India/South-Asia-relevant content that "
                      f"translates cleanly. {SCHEMA}")
            user = (f"Produce {PER_CALL} fresh, distinct '{task.value}' seeds focused "
                    f"on this angle: {angle}. Make each clearly different from the "
                    f"others. Return ONLY the JSON array.")
            try:
                raw = client.complete(model=TEACHER.split(":", 1)[-1] if ":" in TEACHER else TEACHER,
                                      system=system, user=user, temperature=1.0, max_tokens=1500)
            except Exception as err:
                print(f"  [{task.value}] call {calls} failed: {err}", file=sys.stderr); continue
            for rec in parse_seed_array(raw):
                if len(result.seeds) >= PER_FAMILY: break
                seed = _accept(rec, task, result)
                if seed is None: continue
                key = _normalize(seed.prompt)
                if key in pool_norm or key in seen_local:
                    result._bump("duplicate"); continue
                seen_local.add(key)
                c = len(result.seeds) + 1
                while f"seed-{task.value}-bs-{c:04d}" in taken: c += 1
                seed.id = f"seed-{task.value}-bs-{c:04d}"; taken.add(seed.id)
                seed.metadata = {**seed.metadata, "source": f"creative:{TEACHER}", "angle": angle}
                result.seeds.append(seed)
            print(f"  [{task.value}] call {calls}/{max_calls} (angle {ai}): "
                  f"{len(result.seeds)}/{PER_FAMILY}", file=sys.stderr, flush=True)
        out_seeds.extend(result.seeds)
        print(f"[{task.value}] done: {len(result.seeds)} seeds, drops={dict(result.drops)}", flush=True)

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    path = f"data/seeds/bootstrapped_{ts}.json"
    json.dump({"seeds": [json.loads(s.model_dump_json()) for s in out_seeds]},
              open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nWROTE {path} ({len(out_seeds)} seeds)")


if __name__ == "__main__":
    raise SystemExit(main())
