"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LANGUAGES } from "@/lib/rubric";

export default function Home() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [lang, setLang] = useState("");

  const ready = lang.length > 0;

  return (
    <>
      <h1>Native-speaker rating</h1>
      <p className="muted">
        You&apos;ll see ~20 short machine-generated tasks in your language. Rate each on
        three quick questions. There are no right answers: your honest judgement as a
        native speaker is exactly what we need.
      </p>

      <div className="card">
        <label htmlFor="lang">Language you&apos;re rating</label>
        <select id="lang" value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="">Select a language…</option>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.name}
            </option>
          ))}
        </select>

        <label htmlFor="name">Your name (optional)</label>
        <input
          id="name"
          type="text"
          placeholder="So we can thank you — leave blank to stay anonymous"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <div style={{ marginTop: 20 }}>
          <button
            disabled={!ready}
            onClick={() => {
              // Anonymous, collision-free identity per session — the rater never
              // types or manages an ID. A fresh "Start" = a fresh rater, so a
              // shared device (friend → parent) doesn't conflate two people.
              const rater = crypto.randomUUID();
              const q = new URLSearchParams({ lang, rater });
              if (name.trim()) q.set("name", name.trim());
              router.push(`/rate?${q.toString()}`);
            }}
          >
            Start rating →
          </button>
        </div>
      </div>

      <div className="card">
        <h2>What the three questions mean</h2>
        <p>
          <strong>Naturalness</strong>: does it read like a native speaker wrote it?
          (You won&apos;t see the English for this one.)
        </p>
        <p>
          <strong>Meaning match</strong>: does it say the same thing as the English
          original? (Meaning only; ignore how good the language is.)
        </p>
        <p>
          <strong>Cultural fit</strong>: does it feel written for your language&apos;s
          readers, or like a translated foreign text?
        </p>
        <p className="muted">These three are independent — please judge each on its own.</p>
      </div>
    </>
  );
}
