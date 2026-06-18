# Teacher bake-off — Hindi (`hi`)

Models compared: `qwen/qwen3.5-122b-a10b`, `sarvamai/sarvam-m`, `deepseek-ai/deepseek-v4-flash`

## seed-qa-001 — qa

**English seed:** What year did the first man walk on the moon?
  
**Reference answer:** 1969

### `qwen/qwen3.5-122b-a10b`
> ⚠️ ERROR: NVIDIA API call failed after 4 attempts: Request timed out.

### `sarvamai/sarvam-m`
- **prompt:** Okay, let's tackle this translation task. The user wants the English question "What year did the first man walk on the moon?" translated into Hindi, following specific rules. First, I need to ensure the translation is natural and fluent in Hindi, not a literal word-for-word conversion. The key here is to maintain the exact meaning, difficulty, and any reasoning steps.

The original question is straightforward, asking for a specific year. The reference answer is "1969". So the Hindi translation should ask the same question. Let me think about the structure. In Hindi, the common way to ask "what year" is "किस वर्ष" or "साल क्या था". But "What year did..." would be more like "किस वर्ष पहले मनुष्य ने चंद्रमा पर पैर रखा?" or "पहले मनुष्य ने चंद्रमा पर कब पैर रखा?" Wait, but the original uses "walked on the moon", which is "चंद्रमा पर पैर रखा". That's correct. 

I need to make sure the sentence structure is natural. "पहले मनुष्य ने चंद्रमा पर कब पैर रखा?" might be better because "कब" (when) is more natural than "किस वर्ष" here. But the original question specifically asks for the year, so maybe using "किस वर्ष" is better to match the structure. Let me check. "What year did..." translates to "किस वर्ष हुआ" or "किस वर्ष में हुआ". So perhaps "पहले मनुष्य ने किस वर्ष चंद्रमा पर पैर रखा?" That's more accurate. 

Yes, that structure directly translates the question while maintaining the meaning. The expected answer in Hindi would be "1969", written in Devanagari numerals: "१९६९". Wait, but the reference answer is in English. The user's example shows the expected answer in English as "1969". But according to the instructions, the expected answer should be in Hindi. Wait, the user's example has {"expected": "1969"}, but the instruction says to write entirely in Hindi. So maybe the expected answer should be in Hindi numerals. Let me confirm. The user's example shows the expected answer in English, but the rules state to write entirely in Hindi. So the answer should be in Hindi numerals. So "1969" in Hindi is "१९६९". Therefore, the JSON should have "expected": "१९६९".

Putting it all together: the prompt in Hindi is "पहले मनुष्य ने किस वर्ष चंद्रमा पर पैर रखा?" and the expected answer is "१९६९". I need to ensure there are no English words and that the translation is accurate. Yes, this meets all the rules.
</think>

{"prompt": "पहले मनुष्य ने चंद्रमा पर किस वर्ष पैर रखा?", "expected": "1969"}
- **expected:** None

### `deepseek-ai/deepseek-v4-flash`
- **prompt:** पहला मानव चाँद पर किस वर्ष चला था?
- **expected:** 1969

## seed-qa-002 — qa

**English seed:** What is the capital city of Brazil?
  
**Reference answer:** Brasilia

### `qwen/qwen3.5-122b-a10b`
> ⚠️ ERROR: NVIDIA API call failed after 4 attempts: Request timed out.

### `sarvamai/sarvam-m`
- **prompt:** ब्राज़ील की राजधानी शहर क्या है?
- **expected:** ब्रासीलिया

### `deepseek-ai/deepseek-v4-flash`
- **prompt:** ब्राजील की राजधानी क्या है?
- **expected:** ब्रासीलिया
