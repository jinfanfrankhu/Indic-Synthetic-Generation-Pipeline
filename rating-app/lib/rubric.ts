// The three rating axes, mirroring syndata's QualityAxis + the gold-standard
// protocol. Plain-language labels for raters; the keys match the analysis join.

export const INSTRUCTIONS_VERSION = "v1";

export type AxisKey = "fluency" | "faithfulness" | "bias";

export interface Axis {
  key: AxisKey;
  label: string;
  needsSource: boolean; // show the English source when rating this axis?
  question: string;
  anchors: Record<1 | 2 | 3 | 4, string>;
}

export const AXES: Axis[] = [
  {
    key: "fluency",
    label: "Naturalness",
    needsSource: false,
    question: "Does this read like something a fluent, educated native speaker would write?",
    anchors: {
      1: "Ungrammatical or clearly not written by a native speaker",
      2: "Understandable, but awkward or stilted ('translationese')",
      3: "Natural, with only minor slips",
      4: "Indistinguishable from a fluent native writer",
    },
  },
  {
    key: "faithfulness",
    label: "Meaning match",
    needsSource: true,
    question:
      "Does the version above ask for — or say — the same thing as the English original? Judge meaning only (not how good the language is, not whether any answer is factually correct).",
    anchors: {
      1: "Different meaning, contradicts, or unrelated to the English",
      2: "Same topic, but the task or key details changed",
      3: "Same meaning, with minor drift",
      4: "Fully preserves the English intent; nothing added or lost",
    },
  },
  {
    key: "bias",
    label: "Cultural fit",
    needsSource: true,
    question:
      "Does this feel written for readers of this language, or like a foreign text wearing its clothes? (Watch for English/Western names, examples, units, or framing left in by accident.)",
    anchors: {
      1: "Imposes English/Western framing; clearly foreign",
      2: "Noticeably foreign in places",
      3: "Mostly appropriate",
      4: "Culturally natural for this audience",
    },
  },
];

export const LANGUAGES: { code: string; name: string }[] = [
  { code: "hi", name: "Hindi (हिन्दी)" },
  { code: "ur", name: "Urdu (اردو)" },
  { code: "ta", name: "Tamil (தமிழ்)" },
  { code: "ml", name: "Malayalam (മലയാളം)" },
];

// Items shown per session (raters "go through ~20 tasks").
export const ITEMS_PER_SESSION = 20;

export interface BundleItem {
  task_id: string;
  language: string;
  task_family: string;
  source_prompt: string | null;
  source_expected: string | null;
  generated_prompt: string;
  generated_expected: string | null;
  show_source: boolean;
}
