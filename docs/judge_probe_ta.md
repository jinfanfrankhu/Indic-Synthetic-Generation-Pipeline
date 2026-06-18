# Judge-panel validation

Judges: `sarvamai/sarvam-m`, `mistralai/mistral-small-4-119b-2603`, `z-ai/glm-5.1`, `nvidia/nemotron-3-super-120b-a12b`

Spread = max−min across judges (lower = more agreement). The CONTROL rows feed judges raw English as if it were the generation; fluency there should be **low** — a judge that scores it high is not discriminating.

## ta-clean — _all Tamil (baseline)_

**Seed:** What year did the first man walk on the moon?
**Judged text:** முதல் மனிதர் எந்த ஆண்டில் நிலவில் நடந்தார்?

| Judge | fluency | faithfulness | bias | overall |
|---|---|---|---|---|
| `sarvamai/sarvam-m` | 0.90 | 1.00 | 0.90 | **0.93** |
| `mistralai/mistral-small-4-119b-2603` | 1.00 | 1.00 | 1.00 | **1.00** |
| `z-ai/glm-5.1` | 1.00 | 1.00 | 1.00 | **1.00** |
| `nvidia/nemotron-3-super-120b-a12b` | 0.90 | 1.00 | 1.00 | **0.97** |
| _spread_ | 0.10 | 0.00 | 0.10 | |

- `sarvamai/sarvam-m`: The generated Tamil task is grammatically correct and naturally phrased, preserving the original meaning and difficulty. It uses appropriate Tamil vocabulary without English-centric assumptions, though 'நிலவில்' (on the moon) is slightly poetic compared to more common 'சந்திரனில்'.
- `mistralai/mistral-small-4-119b-2603`: The Tamil question is grammatically correct and natural, and it faithfully translates the English seed task. The answer is accurate and culturally neutral.
- `z-ai/glm-5.1`: The Tamil translation is perfectly natural, grammatically correct, and accurately preserves the meaning and difficulty of the original English seed. The question is about a universal historical/scientific fact, so there are no cultural localization issues.
- `nvidia/nemotron-3-super-120b-a12b`: The Tamil sentence is grammatically correct and natural, accurately translating the English question about the year of the first moon walk. It retains the original meaning and contains no foreign cultural bias.

## ta-codeswitch-1 — _one English word ('moon')_

**Seed:** What year did the first man walk on the moon?
**Judged text:** முதல் மனிதர் எந்த ஆண்டில் moon-ல் நடந்தார்?

| Judge | fluency | faithfulness | bias | overall |
|---|---|---|---|---|
| `sarvamai/sarvam-m` | 0.50 | 1.00 | 0.70 | **0.73** |
| `mistralai/mistral-small-4-119b-2603` | 0.30 | 0.90 | 0.80 | **0.67** |
| `z-ai/glm-5.1` | 0.50 | 1.00 | 1.00 | **0.83** |
| `nvidia/nemotron-3-super-120b-a12b` | 0.20 | 0.90 | 0.70 | **0.60** |
| _spread_ | 0.30 | 0.10 | 0.30 | |

- `sarvamai/sarvam-m`: The Tamil task uses the English word 'moon' instead of the Tamil term 'நிலா', making it unnatural. The question structure is grammatically correct but contains a cultural/language mismatch.
- `mistralai/mistral-small-4-119b-2603`: The generated Tamil task uses 'moon' in English instead of the Tamil word 'சந்திரன்', making it unnatural Tamil. The rest of the sentence is grammatically correct but the inclusion of an English word breaks fluency.
- `z-ai/glm-5.1`: The generated Tamil task leaves the word 'moon' untranslated as 'moon-ல்' instead of using the native Tamil word 'நிலாவில்' (nilāvil), which breaks the natural flow and fluency. However, the meaning and difficulty of the original seed are perfectly preserved, and the topic itself is culturally neutral.
- `nvidia/nemotron-3-super-120b-a12b`: The Tamil sentence mixes native grammar with the English word 'moon', making it sound unnatural to a native speaker and lowering fluency. The meaning and intent of the original question are fully preserved, and the only bias is the minor use of an English loanword rather than a fully localized term.

## ta-codeswitch-heavy — _several English words_

**Seed:** What year did the first man walk on the moon?
**Judged text:** First man எந்த year-ல் moon-ல் நடந்தார்?

| Judge | fluency | faithfulness | bias | overall |
|---|---|---|---|---|
| `sarvamai/sarvam-m` | 0.60 | 1.00 | 0.70 | **0.77** |
| `mistralai/mistral-small-4-119b-2603` | 0.00 | 0.70 | 0.20 | **0.30** |
| `z-ai/glm-5.1` | 0.20 | 1.00 | 1.00 | **0.73** |
| `nvidia/nemotron-3-super-120b-a12b` | 0.00 | 1.00 | 0.20 | **0.40** |
| _spread_ | 0.60 | 0.30 | 0.80 | |

- `sarvamai/sarvam-m`: The Tamil task uses English words ('moon', 'year') and an unnatural structure ('First man'), reducing fluency. The meaning is preserved but with awkward phrasing.
- `mistralai/mistral-small-4-119b-2603`: The generated Tamil task mixes English words ('First man', 'year', 'moon') with Tamil morphology, resulting in unnatural Tamil. The reference answer is correct but the task itself is not properly localized Tamil.
- `z-ai/glm-5.1`: The generated Tamil task heavily mixes English words ('First', 'year', 'moon') with Tamil, making it grammatically unnatural and failing to demonstrate proper Tamil vocabulary for a simple question. However, the core meaning is preserved, and the topic is globally neutral.
- `nvidia/nemotron-3-super-120b-a12b`: The generated text mixes English words with Tamil, so it is not fluent Tamil; however, the meaning and intent are preserved, and the use of English words shows a lack of localization.

## ta-english — _full English (trivial control)_

**Seed:** What year did the first man walk on the moon?
**Judged text:** What year did the first man walk on the moon?

| Judge | fluency | faithfulness | bias | overall |
|---|---|---|---|---|
| `sarvamai/sarvam-m` | 0.00 | 1.00 | 0.00 | **0.33** |
| `mistralai/mistral-small-4-119b-2603` | 0.00 | 1.00 | 0.00 | **0.33** |
| `z-ai/glm-5.1` | 0.00 | 1.00 | 0.00 | **0.33** |
| `nvidia/nemotron-3-super-120b-a12b` | 0.00 | 1.00 | 0.00 | **0.33** |
| _spread_ | 0.00 | 0.00 | 0.00 | |

- `sarvamai/sarvam-m`: The generated task is identical to the English seed, written in English rather than Tamil. This violates the requirement for Tamil output, making fluency 0.0. Faithfulness is 1.0 as the meaning is preserved, but bias is 0.0 due to lack of localization.
- `mistralai/mistral-small-4-119b-2603`: The generated task and answer are entirely in English, not Tamil.
- `z-ai/glm-5.1`: The generated task and answer are entirely in English, with no Tamil translation provided. Per the hard rule, fluency must be 0.0 because the text is not written in Tamil. Faithfulness is high as it copies the English exactly, and bias is 0.0 due to the complete lack of localization.
- `nvidia/nemotron-3-super-120b-a12b`: The generated text remains in English, not Tamil, so fluency is 0.0; the question and answer correctly preserve the original meaning, giving faithfulness 1.0; however, the content is not localized and retains an English-centric framing, resulting in bias 0.0.
