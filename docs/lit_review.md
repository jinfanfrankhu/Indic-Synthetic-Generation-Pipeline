

## Bactrian-X paper: https://arxiv.org/abs/2305.15011

 - Bactrian-X is a multilingual dataset of instruction-response pairs across 52 languages
 - Using this, train adapters using low-rank adaptation (LoRA) which integrate LLMs (frozen)
 - Adapters are small trainable modules (weights, neurons, etc) injected into the transformer at the attention weight matrices. If a normal output is W * x, in LoRA output = W * x + (B * A) * x. Therefore W_eff = W + BA
 - LoRA based models outperform both vanilla models (just token prediction) and instruction-tuned models (assistant type models)


## MURI paper: https://arxiv.org/abs/2409.12958

 - MURI, Multilingual Reverse Instructions, generates instruction-tuning datasets for LRLangs without needing human annotation or pre-existing multilingual models
 - instead of responding to: "write me an article," instead, it responds to: "what question could have prompted this article?"
 - pretty effective for NLU (Natural Language Understanding)


## UPDESH paper: https://arxiv.org/abs/2509.21294

 - UPDESH: a high-quality large-scale instruction-following dataset across 13 Indian languages and English
 - Use both Top-down data generation (start with English, then translate. ie, Bactrian-X) and bottom-up (how MURI approaches)
    - Top-down is only used for reasoning tasks (culture-agnostic) while generative tasks use bottom-up (needs cultural grounding)
 - Used data filtration using tool called IndicLID. If model isn't 75% sure output is in target language, output is dropped. If more than 75% of words are repeated, output is dropped.
 - Used GPT-4o as an automated judge and compared against native speakers. over 90% agreement for toxicity, problematic content, and cultural relevance. Only ~50% agreement on repetitiveness, persona adherence, and linguistic plausibility.
 - Models trained on UPDESH get consistent improvement in NLU and NLG (Natural Language Generation)


## How Reliable are LLM-as-judge paper: https://arxiv.org/abs/2505.12201

 - LLMs struggle to achieve consistent judgement across languages with average Fleiss' Kappa = ~0.3
 - Particularly poor performance in low-resource languages
 - Neither training on multilingual data nor increasing model scale improves judgement consistency
 - Prompts with explanation generation consistently achieve better consistency results
 - Proposed fix is ensemble: majority voting across multiple models
 - Telugu called out as once of the worst performers: 0.002 Cohen's Kappa...


## Alpaca - Stanford: https://crfm.stanford.edu/2023/03/13/alpaca.html

 - Fine-tune Meta's LLaMa 7B model to Alpaca. Used OpenAI API to generate instruction following examples from seeds.
 - LLaMa 7B was just text, didn't have instruction-tuning.


## Sentence-BERT / sentence-transformers: https://arxiv.org/abs/1908.10084

 - Why we use it: the back-translation filter needs a semantic-similarity score between the English seed and the back-translated generation. SBERT encodes each sentence to a fixed vector once, so similarity is a single cosine — O(1) per pair, runs locally, no extra teacher/judge API calls (matters under the 40/min NVIDIA cap).
 - Contrast with the obvious alternatives:
    - **BERTScore** does token-level greedy matching every comparison (no reusable sentence vector) and correlates with fluency more than with adequacy — heavier and less aligned with what we want to measure.
    - **spBLEU/ChrF** (the FLORES MT metrics) are surface n-gram overlap; back-translation paraphrases heavily, so lexical overlap punishes valid paraphrases. Embedding cosine is meaning-level, which is the right granularity for a consistency check.
 - SBERT vs. vanilla BERT: averaging BERT's token vectors gives sentence embeddings *worse* than GloVe for similarity; SBERT's siamese fine-tuning on NLI/STS is what makes cosine meaningful. So "use sentence-transformers" is a deliberate choice, not just "embed with a transformer."
 - Multilingual: Reimers & Gurevych (2020) distill a multilingual student so paraphrase-multilingual MiniLM/mpnet land translations and their source in a *shared* space — cross-lingual cosine is meaningful, which is exactly the back-translation setup (English seed vs. back-translated English, but also lets us sanity-check target-language pairs in one space). Models cover all four of our languages.
 - Practical: relative score only (we threshold against the gold set in Phase B, not an absolute cutoff); pick a paraphrase-multilingual model for speed, document the exact checkpoint for reproducibility.
