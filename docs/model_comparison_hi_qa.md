# Teacher bake-off — Hindi (`hi`)

Models compared: `gemini:gemini-3.1-flash-lite`, `gemini:gemma-4-31b-it`, `gemini:gemini-2.5-flash`, `gemini:gemini-3.5-flash`

## seed-qa-001 — qa

**English seed:** What year did the first man walk on the moon?
  
**Reference answer:** 1969

### `gemini:gemini-3.1-flash-lite`
- **prompt:** किस वर्ष में पहले व्यक्ति ने चंद्रमा पर कदम रखा था?
- **expected:** 1969

### `gemini:gemma-4-31b-it`
- **prompt:** <thought>*   English task: "What year did the first man walk on the moon?"
    *   Reference answer: "1969"
    *   Goal: Translate into natural, fluent Hindi for instruction-tuning data.
    *   Constraints: Entirely in Hindi, no English words, no code-switching, no literal word-for-word translation, output only a JSON object.

    *   "What year did the first man walk on the moon?"
    *   Direct translation: पहले आदमी ने चाँद पर किस साल कदम रखा? (Pahle aadmi ne chaand par kis saal kadam rakha?)
    *   More natural/formal Hindi: चंद्रमा पर पहले मनुष्य ने किस वर्ष कदम रखा था? (Chandrama par pahle manushya ne kis varsh kadam rakha tha?) or चाँद पर पहला इंसान किस साल पहुँचा था? (Chaand par pahla insaan kis saal pahuncha tha?)
    *   Selection: "चंद्रमा पर पहले मनुष्य ने किस वर्ष कदम रखा था?" is precise and natural.

    *   "1969"
    *   In Hindi numerals: १९६९. However, in modern Hindi contexts, Arabic numerals (1969) are standard and widely accepted. But the prompt says "Do not leave any English words". Numbers are symbols, but to be safe and strictly "Hindi", I should consider if numbers are considered "English". Usually, they aren't, but let's check if words are needed. "उन्नीस सौ उनहत्तर" (Nineteen sixty-nine). However, for a fact-based question, the numeric form is standard. I will use the digits "1969" as they are universal, or "१९६९". Let's stick to "1969" as it's standard in Hindi text, or spell it out if the constraint is extremely strict. Actually, "1969" is fine.

    *   `prompt`: "चंद्रमा पर पहले मनुष्य ने किस वर्ष कदम रखा था?"
    *   `expected`: "1969" (or "१९६९"). I'll use "1969" as it's the standard representation in modern Hindi.

    *   Entirely in Hindi? Yes.
    *   No English words? Yes.
    *   Natural/fluent? Yes.
    *</thought>
- **expected:** None

### `gemini:gemini-2.5-flash`
- **prompt:** पहले इंसान ने चाँद पर किस वर्ष कदम रखा था?
- **expected:** 1969

### `gemini:gemini-3.5-flash`
> ⚠️ ERROR: API call to gemini-3.5-flash failed after 4 attempts: Error code: 503 - [{'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}]

## seed-qa-002 — qa

**English seed:** What is the capital city of Brazil?
  
**Reference answer:** Brasilia

### `gemini:gemini-3.1-flash-lite`
- **prompt:** ब्राज़ील की राजधानी कौन सा शहर है?
- **expected:** ब्रासीलिया

### `gemini:gemma-4-31b-it`
- **prompt:** <thought>*   English task: "What is the capital city of Brazil?"
    *   Reference answer: "Brasilia"
    *   Target language: Hindi.
    *   Output format: JSON object with keys "prompt" and "expected".
    *   Constraints: Entirely in Hindi, no English words, natural/fluent translation, no markdown fences.

    *   Task: "What is the capital city of Brazil?" -> "ब्राजील की राजधानी कौन सा शहर है?" or "ब्राजील की राजधानी क्या है?" (The second one is more natural).
    *   Answer: "Brasilia" -> "ब्रासीलिया".

    *   Prompt: "ब्राजील की राजधानी क्या है?"
    *   Expected: "ब्रासीलिया"

    *   Entirely in Hindi? Yes.
    *   No English words? Yes.
    *   Natural/fluent? Yes.
    *   Single JSON object? Yes.
    *   No markdown fences? Yes.

    `{"prompt": "ब्राजील की राजधानी क्या है?", "expected": "ब्रासीलिया"}`</thought>{"prompt": "ब्राजील की राजधानी क्या है?", "expected": "ब्रासीलिया"}
- **expected:** None

### `gemini:gemini-2.5-flash`
- **prompt:** ब्राजील की राजधानी क्या है?
- **expected:** ब्रासीलिया

### `gemini:gemini-3.5-flash`
> ⚠️ ERROR: API call to gemini-3.5-flash failed after 4 attempts: Error code: 503 - [{'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}]
