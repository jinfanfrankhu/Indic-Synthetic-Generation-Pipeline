"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LANGUAGES } from "@/lib/rubric";

export default function Home() {
  const router = useRouter();
  const [rater, setRater] = useState("");
  const [lang, setLang] = useState("");

  const ready = rater.trim().length > 0 && lang.length > 0;

  return (
    <>
      <h1>Native-speaker rating</h1>
      <p className="muted">
        You&apos;ll see ~20 short machine-generated tasks in your language. Rate each on
        three quick questions. There are no right answers — your honest judgement as a
        native speaker is exactly what we need.
      </p>

      <div className="card">
        <label htmlFor="rater">Your rater ID</label>
        <input
          id="rater"
          type="text"
          placeholder="e.g. your name or the ID we sent you"
          value={rater}
          onChange={(e) => setRater(e.target.value)}
        />

        <label htmlFor="lang">Language you&apos;re rating</label>
        <select id="lang" value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="">Select a language…</option>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.name}
            </option>
          ))}
        </select>

        <div style={{ marginTop: 20 }}>
          <button
            disabled={!ready}
            onClick={() =>
              router.push(`/rate?lang=${lang}&rater=${encodeURIComponent(rater.trim())}`)
            }
          >
            Start rating →
          </button>
        </div>
      </div>

      <div className="card">
        <h2>What the three questions mean</h2>
        <p>
          <strong>Naturalness</strong> — does it read like a native speaker wrote it?
          (You won&apos;t see the English for this one.)
        </p>
        <p>
          <strong>Meaning match</strong> — does it say the same thing as the English
          original? (Meaning only — ignore how good the language is.)
        </p>
        <p>
          <strong>Cultural fit</strong> — does it feel written for your language&apos;s
          readers, or like a translated foreign text?
        </p>
        <p className="muted">These three are independent — please judge each on its own.</p>
      </div>
    </>
  );
}
