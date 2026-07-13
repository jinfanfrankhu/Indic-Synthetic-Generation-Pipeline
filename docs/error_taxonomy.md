# Error Taxonomy - Synthetic Corpus Spot-Check

_Generated 2026-07-13. Full-corpus surrogate review of all 1335 items (LLM reviewers, model=Sonnet; NOT native speakers - fluency judgments are low-confidence and flagged as such). Correctness (math/facts), format, script/language, faithfulness vs. English seed, and truncation are checked deterministically or verifiably._

## Overview

| Verdict | Count | Share |
| --- | --- | --- |
| ok | 1225 | 91.8% |
| minor | 62 | 4.6% |
| defect | 48 | 3.6% |
| **total** | 1335 | 100% |

## By language

| Language | ok | minor | defect | defect rate |
| --- | --- | --- | --- | --- |
| hi | 290 | 25 | 9 | 2.8% |
| ur | 318 | 13 | 8 | 2.4% |
| ta | 300 | 13 | 20 | 6.0% |
| ml | 317 | 11 | 11 | 3.2% |

## By error category (defect + minor)

| Category | Count |
| --- | --- |
| format-failure | 57 |
| translation-drift | 27 |
| other | 24 |
| unfaithful | 7 |
| logic-error | 6 |
| wrong-language | 2 |
| factual-error | 2 |
| disfluent | 2 |
| cultural-oddity | 2 |
| label-invalid | 1 |

## Defect examples (representative)

### format-failure
- **syn-hi-classification-bs-0021-024** (hi/classification) - Prompt never lists the answer options (no विकल्प), unlike labels metadata; model has no visible label set to choose from.
  - prompt: निम्नलिखित स्थिति की कानूनी स्थिति निर्धारित करें: 'एक व्यक्ति बिना कॉपीराइट स्वामी की अनु...
  - expected: कॉपीराइट उल्लंघन
- **syn-hi-classification-bs-0027-029** (hi/classification) - Prompt gives no options list; genre labels only exist in metadata, not shown to the model.
  - prompt: नीचे दी गई पुस्तक की संक्षिप्त कथा के आधार पर उसकी विधा (जॉनर) पहचानें: '1920 के दशक के लं...
  - expected: रहस्य

### translation-drift
- **syn-hi-translation-002-001** (hi/translation) - prompt has no embedded English source; prompt and expected are just two Hindi paraphrases of 'nearest market'.
  - prompt: निकटतम बाज़ार कहाँ है?
  - expected: सबसे नज़दीकी बाज़ार कहाँ है?
- **syn-hi-translation-bs-0010-013** (hi/translation) - prompt has no embedded English source; prompt and expected are two slightly different Hindi paraphrases (headache/pharmacy).
  - prompt: मेरे सिर में बहुत तेज दर्द है और मुझे तुरंत एक दवा की दुकान ढूंढने की जरूरत है।
  - expected: मुझे बहुत तेज सिरदर्द है और मुझे तत्काल एक फार्मेसी खोजने की आवश्यकता है।

### unfaithful
- **syn-hi-instruction-bs-0015-019** (hi/instruction) - Prompt asks to write the actual vegan lasagna recipe; response only meta-describes substitutions, gives no real recipe steps/ingredients list.
  - prompt: पारंपरिक लसानिया को शाकाहारी (वेगन) रूप में बनाने की विधि लिखिए। इसमें मांस और डेयरी उत्पा...
  - expected: एक विस्तृत रेसिपी जिसमें मांस की जगह सोया के कीमे या मशरूम का उपयोग हो, और डेयरी की जगह का...

### logic-error
- **syn-hi-reasoning-bs-0008-013** (hi/reasoning) - Answer Alice,Bob,Charlie puts Alice adjacent to Bob, violating the stated constraint; correct order is Bob,Charlie,Alice. Error inherited from EN seed.
  - prompt: तीन मित्र (ऐलिस, बॉब और चार्ली) एक पंक्ति में बैठे हैं। ऐलिस, बॉब के बगल में नहीं है। चार्...
  - expected: क्रम है: ऐलिस, बॉब, चार्ली। तर्क: चूँकि चार्ली बॉब के ठीक दाईं ओर है, इसलिए वे एक साथ (बॉब...
- **syn-ml-reasoning-bs-0008-013** (ml/reasoning) - Order Alice,Bob,Charlie has Alice adjacent to Bob (pos1,2), violating 'Alice not next to Bob'; correct order is Bob,Charlie,Alice.
  - prompt: മൂന്ന് സുഹൃത്തുക്കൾ (ആലീസ്, ബോബ്, ചാർലി) ഒരു വരിയിൽ ഇരിക്കുകയാണ്. ആലീസ് ബോബിന്റെ അടുത്തല്ല...
  - expected: ഇടതുവശത്തുനിന്ന് വലതുവശത്തേക്കുള്ള ക്രമം ആലീസ്, ബോബ്, ചാർലി എന്നിങ്ങനെയാണ്. കാരണം: ചാർലി ബ...

### factual-error
- **syn-ml-classification-bs-0023-026** (ml/classification) - expected 'താപമണ്ഡലം' means thermosphere, not stratosphere (should be 'സമതാപമണ്ഡലം') — wrong label picked for seed answer.
  - prompt: യാത്രാവിമാനങ്ങൾ അസ്വസ്ഥതകൾ ഒഴിവാക്കുന്നതിനായി സാധാരണയായി സഞ്ചരിക്കുന്ന അന്തരീക്ഷത്തിലെ പാള...
  - expected: താപമണ്ഡലം
- **syn-ta-instruction-bs-0013-017** (ta/instruction) - Item 5 labels lunges as 'நுரையீரல் பயிற்சி' which means 'lung exercise', a mistranslation of 'lunges'.
  - prompt: எந்தவிதமான உடற்பயிற்சிக் கருவிகளும் இன்றி, சிறிய அடுக்குமாடி குடியிருப்பில் வசிக்கும் ஒருவ...
  - expected: 1. தண்டால் (புஷ்-அப்ஸ்) - இது மார்பு மற்றும் கைகளின் வலிமையை அதிகரிக்கும். 2. உட்கார்ந்து ...

### label-invalid
- **syn-ml-classification-102-001** (ml/classification) - expected 'തടസ്ഥമില്ലാത്തത്' is a non-standard/garbled word, doesn't mean 'neutral' (should be 'നിഷ്പക്ഷം' or 'ന്യൂട്രൽ').
  - prompt: രാവിലെ ആറു മണിക്ക് നാലാം നമ്പർ പ്ലാറ്റ്‌ഫോമിൽ നിന്ന് ട്രെയിൻ പുറപ്പെടും. ഈ വാചകത്തിന്റെ വി...
  - expected: തടസ്ഥമില്ലാത്തത്

## Curation hook

All 110 flagged items (48 defect + 62 minor) written to `data/filtered/review_flags.jsonl` (id, lang, task, verdict, categories, note) for a drop/fix pass. Recommended: drop the 48 defects from the published set; hand-check the 62 minors. This is a surrogate review - a native-speaker pass would refine especially the fluency and cultural-oddity judgments.
