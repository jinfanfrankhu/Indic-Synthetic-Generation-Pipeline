"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AXES,
  BundleItem,
  INSTRUCTIONS_VERSION,
  ITEMS_PER_SESSION,
} from "@/lib/rubric";

type Scores = { fluency?: number; faithfulness?: number; bias?: number };

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function Scale({
  value,
  onChange,
  anchors,
}: {
  value?: number;
  onChange: (v: number) => void;
  anchors: Record<number, string>;
}) {
  return (
    <>
      <div className="scale">
        {[1, 2, 3, 4].map((n) => (
          <button
            key={n}
            type="button"
            className={value === n ? "selected" : ""}
            onClick={() => onChange(n)}
          >
            {n}
          </button>
        ))}
      </div>
      <div className="anchors">
        {[1, 2, 3, 4].map((n) => (
          <div key={n}>{anchors[n]}</div>
        ))}
      </div>
    </>
  );
}

export default function RatingFlow() {
  const params = useSearchParams();
  const lang = params.get("lang") ?? "";
  const rater = params.get("rater") ?? "";
  const name = params.get("name") ?? "";
  const displayName = name || "anonymous";

  const [allItems, setAllItems] = useState<BundleItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [phase, setPhase] = useState<"A" | "B">("A");
  const [scores, setScores] = useState<Scores>({});
  const [unsure, setUnsure] = useState(false);
  const [comment, setComment] = useState("");
  const [startedAt, setStartedAt] = useState<string>(() => new Date().toISOString());
  const [submitting, setSubmitting] = useState(false);

  // Load the blind bundle and pick this language's session items.
  useEffect(() => {
    fetch("/rater_bundle.json")
      .then((r) => r.json())
      .then((b) => {
        const mine = (b.items as BundleItem[]).filter((it) => it.language === lang);
        setAllItems(shuffle(mine).slice(0, ITEMS_PER_SESSION));
      })
      .catch((e) => setError(String(e)));
  }, [lang]);

  const items = allItems ?? [];
  const item = items[idx];

  const fluencyAxis = AXES.find((a) => a.key === "fluency")!;
  // Bottom-up items have no English source, so "Meaning match" (faithfulness)
  // can't be judged — there's nothing to compare against. Drop that axis and the
  // English panel for them; fluency and cultural fit still apply.
  const hasSource = item?.show_source ?? Boolean(item?.source_prompt);
  const phaseBAxes = AXES.filter(
    (a) => a.needsSource && (hasSource || a.key !== "faithfulness")
  );

  const phaseBReady = phaseBAxes.every((a) => scores[a.key] != null);

  async function submitCurrent() {
    if (!item || !phaseBReady) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/ratings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: item.task_id,
          rater_id: rater,
          rater_name: name || null,
          language: item.language,
          task_family: item.task_family,
          fluency: scores.fluency,
          faithfulness: scores.faithfulness ?? null,
          bias: scores.bias,
          unsure,
          comment: comment.trim() || null,
          instructions_version: INSTRUCTIONS_VERSION,
          started_at: startedAt,
          submitted_at: new Date().toISOString(),
        }),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || "save failed");
      // advance
      setIdx((i) => i + 1);
      setPhase("A");
      setScores({});
      setUnsure(false);
      setComment("");
      setStartedAt(new Date().toISOString());
    } catch (e) {
      setError("Couldn't save that rating — check your connection and try again. " + String(e));
    } finally {
      setSubmitting(false);
    }
  }

  // ---- guards ----
  if (!lang || !rater) {
    return (
      <>
        <p>Missing language or rater ID.</p>
        <Link href="/">← Back to start</Link>
      </>
    );
  }
  if (error && !item) {
    return (
      <>
        <p>Couldn&apos;t load the items: {error}</p>
        <Link href="/">← Back to start</Link>
      </>
    );
  }
  if (allItems === null) return <p className="muted">Loading items…</p>;
  if (items.length === 0) {
    return (
      <>
        <p>No items found for this language yet.</p>
        <Link href="/">← Back to start</Link>
      </>
    );
  }
  if (idx >= items.length) {
    return (
      <>
        <h1>All done — thank you! 🙏</h1>
        <p className="muted">
          You rated {items.length} items as <strong>{displayName}</strong>. Your ratings
          are saved. You can close this tab.
        </p>
        <Link href="/">Rate another set →</Link>
      </>
    );
  }

  const pct = Math.round((idx / items.length) * 100);

  return (
    <>
      <div className="row">
        <span className="muted">
          Item {idx + 1} of {items.length}
        </span>
        <span className="muted">{displayName} · {lang}</span>
      </div>
      <div className="progress">
        <span style={{ width: `${pct}%` }} />
      </div>

      {phase === "A" && (
        <div className="card">
          <h2>Read this text</h2>
          <div className="subject" dir="auto" lang={lang}>
            {item.generated_prompt}
          </div>
          {item.generated_expected && (
            <div className="source">
              <div className="lbl">Answer given</div>
              <div dir="auto" lang={lang}>{item.generated_expected}</div>
            </div>
          )}

          <div className="q">
            <span className="ax">{fluencyAxis.label}</span> — {fluencyAxis.question}
          </div>
          <Scale
            value={scores.fluency}
            anchors={fluencyAxis.anchors}
            onChange={(v) => setScores((s) => ({ ...s, fluency: v }))}
          />

          <div style={{ marginTop: 20 }}>
            <button disabled={scores.fluency == null} onClick={() => setPhase("B")}>
              Next →
            </button>
          </div>
        </div>
      )}

      {phase === "B" && (
        <div className="card">
          {hasSource ? (
            <>
              <h2>Now compare to the English</h2>
              <div className="source">
                <div className="lbl">English original</div>
                <div>{item.source_prompt}</div>
                {item.source_expected && (
                  <div className="muted" style={{ marginTop: 6 }}>
                    Reference answer: {item.source_expected}
                  </div>
                )}
              </div>
            </>
          ) : (
            <h2>A couple more questions</h2>
          )}
          <div className="subject" dir="auto" lang={lang}>
            {item.generated_prompt}
          </div>

          {phaseBAxes.map((ax) => (
            <div key={ax.key}>
              <div className="q">
                <span className="ax">{ax.label}</span> — {ax.question}
              </div>
              <Scale
                value={scores[ax.key]}
                anchors={ax.anchors}
                onChange={(v) => setScores((s) => ({ ...s, [ax.key]: v }))}
              />
            </div>
          ))}

          <div className="checkbox-row">
            <input
              id="unsure"
              type="checkbox"
              checked={unsure}
              onChange={(e) => setUnsure(e.target.checked)}
            />
            <label htmlFor="unsure">I&apos;m unsure about this one</label>
          </div>

          <label htmlFor="comment">Comment (optional)</label>
          <textarea
            id="comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Anything odd? e.g. wrong word, foreign phrasing…"
          />

          {error && <p style={{ color: "#f0883e" }}>{error}</p>}

          <div className="row" style={{ marginTop: 20 }}>
            <button className="secondary" onClick={() => setPhase("A")}>
              ← Back
            </button>
            <button disabled={!phaseBReady || submitting} onClick={submitCurrent}>
              {submitting ? "Saving…" : idx + 1 === items.length ? "Save & finish" : "Save & next →"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
