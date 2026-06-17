# Model Selection

Teacher and judge models are drawn from NVIDIA Build's free hosted endpoints (OpenAI-compatible, no self-hosting). Selection optimizes for two axes that matter for this project: **Indic/multilingual quality** (not recency or coding-benchmark strength, which dominate most model marketing) and **teacher≠judge family diversity**, required by the ensemble-judging decision that addresses the ~50% human–LLM agreement on Indic linguistic plausibility reported in UPDESH. The candidate pool was filtered by *model type* first: only general-purpose chat LLMs can serve as teacher or judge, which rules out NVIDIA's safety classifiers and rerankers despite their "free endpoint" availability. The three chat LLMs below go into a small bake-off (same hi/ta seeds through each, comparing script naturality and JSON adherence); the winner becomes teacher and the judge is locked from a different family.

## Candidates (general chat LLMs)

 - **Qwen3.5-122b-a10b** (`qwen/qwen3.5-122b-a10b`) — current baseline, already wired and producing correct Hindi. 122B MoE / 10B active; one of the strongest open families for Asian-language coverage. https://build.nvidia.com/qwen/qwen3.5-122b-a10b
 - **Sarvam** (3B / 30B / 100B sovereign family) — purpose-built for Indian languages by Sarvam AI, trained with NVIDIA on H100s; supports 22 Indian languages + English, math, and code, with a custom tokenizer up to ~4× more efficient on Indic text. Covers all four targets (hi/ur/ta/ml). The strongest a-priori fit for this project. https://www.sarvam.ai/models · https://www.sarvam.ai/blogs/sarvam-30b-105b
 - **DeepSeek V4 Flash** — capable generalist MoE from a different family than Qwen, so it preserves the bias-avoidance rule; strong judge candidate. Indic quality unverified (coding/agent-marketed), hence in the bake-off rather than assumed. https://build.nvidia.com/deepseek-ai

## Ruled out (wrong model type, not wrong quality)

 - **Nemotron 3.5 Content Safety** / **Llama 3.1 Nemotron Safety Guard 8B** — content-*moderation* classifiers over NVIDIA's 13-category Aegis taxonomy; they output safe/unsafe labels, not fluency/faithfulness/format scores, so they cannot serve as the quality judge. Nemotron 3.5 (Gemma-3-4B base, multilingual across 12 languages, ~97% harmful-content accuracy) is, however, a viable *optional safety-filter pass* in Week 4+. https://huggingface.co/blog/nvidia/nemotron-3-5-content-safety · https://docs.nvidia.com/nim/llama-3-1-nemotron-safety-guard-8b/latest/index.html
 - **rerank-qa-mistral-4b** — a cross-encoder reranker for RAG (relevance logit, 503-token limit, `/ranking` endpoint, not chat). Cannot generate text and does not fit the `ChatClient` interface. https://build.nvidia.com/nvidia/nv-rerankqa-mistral-4b-v3/modelcard
 - **Mistral Large 3 675B** — capable but Mistral historically trails the Qwen/Sarvam tier on Indic scripts; large and slow for marginal multilingual benefit. Deprioritized unless the bake-off contradicts this.
