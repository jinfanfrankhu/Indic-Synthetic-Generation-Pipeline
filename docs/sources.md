# Sources

## CC-100 Corpus Size Data

Conneau, A., Khandelwal, K., Goyal, N., Chaudhary, V., Wenzek, G., Guzmán, F., Grave, E., Ott, M., Zettlemoyer, L., & Stoyanov, V. (2020). Unsupervised cross-lingual representation learning at scale. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics* (pp. 8440–8451). Association for Computational Linguistics. https://arxiv.org/abs/1911.02116

> Per-language corpus sizes (compressed, GB) are reported in Table 6. CC-100 was constructed from January–December 2018 CommonCrawl snapshots using the CC-Net pipeline with cld3 language identification and paragraph-level deduplication.

Wenzek, G., Lachaux, M.-A., Conneau, A., Chaudhary, V., Guzmán, F., Joulin, A., & Grave, E. (2020). CCNet: Extracting high quality monolingual datasets from web crawl data. In *Proceedings of the 12th Language Resources and Evaluation Conference* (pp. 4003–4012). European Language Resources Association. https://arxiv.org/abs/1911.00359

> Describes the CC-Net pipeline used to construct CC-100. Documents language identification, perplexity-based quality filtering, and deduplication methodology.

The CC-100 dataset is publicly available at: https://data.statmt.org/cc-100/

---

## Wikipedia Article Counts

Wikimedia Foundation. (2025). *List of Wikipedias*. Meta-Wiki. Retrieved June 2025, from https://meta.wikimedia.org/wiki/List_of_Wikipedias

> Article counts are approximate and subject to change. Indonesian Wikipedia article counts include a substantial proportion of bot-generated stub articles; effective content density is lower than raw counts suggest.

---

## Speaker Counts

Eberhard, D. M., Simons, G. F., & Fennig, C. D. (Eds.). (2023). *Ethnologue: Languages of the world* (26th ed.). SIL International. https://www.ethnologue.com

> Speaker counts reflect total speakers (native + second-language). Hindi: ~600M; Urdu: ~230M; Tamil: ~80M; Malayalam: ~35M. Note that Hindi and Urdu share a spoken standard (Hindustani); the counts reflect distinct registered speaker communities.

---

## Language Family Classification

Hammarström, H., Forkel, R., Haspelmath, M., & Bank, S. (2023). *Glottolog 5.0*. Max Planck Institute for Evolutionary Anthropology. https://glottolog.org

> Authoritative genealogical classification of the world's languages. Hindi and Urdu are classified as Indo-Aryan (Indo-European > Indo-Iranian > Indo-Aryan); Tamil and Malayalam as South Dravidian (Dravidian > South Dravidian).

---

## Writing System Classification

Daniels, P. T., & Bright, W. (Eds.). (1996). *The world's writing systems*. Oxford University Press.

> Standard reference for script typology. Devanagari, Tamil script, and Malayalam script are all abugida scripts of the Brahmic family, derived ultimately from Brahmi. Nastaliq is a calligraphic style of the Perso-Arabic script family (an abjad), written right-to-left.

---

## Evaluation Benchmarks

### FLORES-200

NLLB Team, Costa-jussà, M. R., Cross, J., Çelebi, O., Elbayad, M., Heafield, K., Heffernan, K., Kalbassi, E., Lam, J., Licht, D., Maillard, J., Sun, A., Wang, S., Wenzek, G., Youngblood, F., Akula, B., Barrault, L., Gonzalez, G. M., Hansanti, P., … Tran, C. (2022). No language left behind: Scaling human-centered machine translation. *arXiv preprint*. https://arxiv.org/abs/2207.04672

> Introduces FLORES-200, a 204-language parallel evaluation benchmark for machine translation derived from English Wikipedia and Wikinews. Covers all four languages in this study. Evaluation uses spBLEU and ChrF metrics.

### XNLI

Conneau, A., Rinott, R., Lample, G., Williams, A., Bowman, S., Schwenk, H., & Stoyanov, V. (2018). XNLI: Evaluating cross-lingual sentence representations. In *Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing* (pp. 2475–2485). https://arxiv.org/abs/1809.05053

> Cross-lingual Natural Language Inference benchmark across 15 languages. Covers Hindi and Urdu; Tamil and Malayalam are not included (coded as 0 in `language_statistics.csv`).

### XTREME

Hu, J., Ruder, S., Siddhant, A., Neubig, G., Firat, O., & Johnson, M. (2020). XTREME: A massively multilingual multi-task benchmark for evaluating cross-lingual generalisation. In *Proceedings of the 37th International Conference on Machine Learning* (pp. 4411–4421). https://arxiv.org/abs/2003.11080

> Nine-task benchmark across 40 typologically diverse languages. All four languages in this study (hi, ur, ta, ml) are represented. Tasks span classification, structured prediction, question answering, and retrieval.

### IndicXTREME

Doddapaneni, S., Aralikatte, R., Ramesh, G., Goyal, S., Khapra, M. M., Kunchukuttan, A., & Kumar, P. (2023). IndicXTREME: A multi-task benchmark for evaluating Indic languages. In *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics* (pp. 1–21). https://arxiv.org/abs/2212.05409

> Nine-task NLU benchmark covering 20 constitutionally recognised Indian languages, including all four languages in this study. Tasks span sentence classification, structured prediction, question answering, and sentence retrieval. Contains 105 evaluation sets, of which 52 are new contributions.

### Belebele

Bandarkar, L., Liang, D., Muller, B., Artetxe, M., Shukla, S. N., Husa, D., Goyal, N., Krishnan, A., Zettlemoyer, L., & Kambadur, M. (2023). The Belebele benchmark: A parallel reading comprehension dataset in 122 language variants. *arXiv preprint*. https://arxiv.org/abs/2308.16884

> Multiple-choice reading comprehension benchmark derived from FLORES-200 passages, covering 122 language variants. Covers all four languages in this study. Each item has four answer choices; chance baseline is 25%.

### SIB-200

Adelani, D. I., Alabi, J. O., Wairagala, M. J. O., Osei, S., Osei-Brefo, B., Winata, G. I., … Ruder, S. (2023). SIB-200: A simple, inclusive, and big evaluation dataset for topic classification in 200+ languages and dialects. *arXiv preprint*. https://arxiv.org/abs/2309.07445

> Topic classification benchmark covering 205 languages with seven categories, derived from FLORES-200 passages. Covers all four languages in this study.

### MASSIVE

FitzGerald, J., Hench, C., Peris, C., Mackie, S., Rottmann, K., Sanchez, A., Nash, C., Urbach, L., Kakarala, V., Singh, R., Ranganath, S., Crist, L., Britan, M., Leeuwis, W., Tur, G., & Natarajan, P. (2022). MASSIVE: A 1M-example multilingual natural language understanding dataset with 51 typologically-diverse languages. *arXiv preprint*. https://arxiv.org/abs/2204.08582

> Multilingual virtual assistant benchmark with 1M utterances across 51 languages, 18 domains, 60 intents, and 55 slot types. Two primary tasks: intent classification and slot filling. Covers all four languages in this study.

### Dakshina

Roark, B., Wolf-Sonkin, L., Kirov, C., Mielke, S. J., Johny, C., Outchkov, I., & Hall, K. (2020). Processing South Asian languages written in the Latin script: The Dakshina dataset. In *Proceedings of the 12th Language Resources and Evaluation Conference* (pp. 2413–2423). https://aclanthology.org/2020.lrec-1.294

> Romanization and transliteration dataset for 12 South Asian languages. Inclusion/exclusion for individual languages not verified from primary source; marked as True/False in `language_statistics.csv`.

### GLUECoS

Khanuja, S., Dandapat, S., Srinivasan, A., Sitaram, S., & Choudhury, M. (2020). GLUECoS: An evaluation benchmark for code-switched NLP. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics* (pp. 3291–3302). https://arxiv.org/abs/2004.12376

> Code-switching benchmark for Hindi-English and Tamil-English mixed text. Tasks include NER, POS tagging, sentiment analysis, NLI, and QA. Urdu and Malayalam are not included (marked False in `language_statistics.csv`).

---

## Sentence Embeddings (back-translation similarity metric)

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In *Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing (EMNLP-IJCNLP)* (pp. 3982–3992). Association for Computational Linguistics. https://arxiv.org/abs/1908.10084

> Introduces SBERT, a siamese/triplet fine-tuning of BERT that produces sentence embeddings whose cosine similarity is semantically meaningful and computable in O(1) per pair, versus BERT's ~65-hour pairwise regression cost on 10k sentences. Justifies using `sentence-transformers` cosine (rather than BERTScore or n-gram metrics) for the back-translation consistency filter: it is fast, local (no API calls), and scores meaning-level adequacy rather than surface overlap.

Reimers, N., & Gurevych, I. (2020). Making monolingual sentence embeddings multilingual using knowledge distillation. In *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)* (pp. 4512–4525). Association for Computational Linguistics. https://arxiv.org/abs/2004.09813

> Distills a multilingual student model so that translations map to nearby points in a shared embedding space, enabling cross-lingual cosine similarity. Basis for the `paraphrase-multilingual-*` checkpoints; covers all four study languages (hi, ur, ta, ml) and supports comparing source-language and back-translated text in one space.

---

## Back-Translation Model (independent MT for the consistency check)

NLLB Team, Costa-jussà, M. R., Cross, J., Çelebi, O., Elbayad, M., Heafield, K., Heffernan, K., Kalbassi, E., Lam, J., Licht, D., Maillard, J., Sun, A., Wang, S., Wenzek, G., Youngblood, F., Akula, B., Barrault, L., Gonzalez, G. M., Hansanti, P., … Tran, C. (2022). No language left behind: Scaling human-centered machine translation. *arXiv preprint*. https://arxiv.org/abs/2207.04672

> Source of `facebook/nllb-200-distilled-1.3B`, the dedicated MT used to back-translate generated items to English for the back-translation consistency filter. Chosen over reusing the Gemini teacher to keep the check *independent* of the generator (avoiding the same-model circularity SPEC.md forbids for judging) and *literal* (MT renders faithfully where an LLM paraphrases). Runs locally, covers all four study languages. License CC-BY-NC-4.0 — an internal QC signal, not redistributed.

Gala, J., Chitale, P. A., Raghavan, A. K., Gumma, V., Doddapaneni, S., Kumar, A., Nawale, J., Sujatha, A., Puduppully, R., Raghavan, V., Kumar, P., Khapra, M. M., Dabre, R., & Kunchukuttan, A. (2023). IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages. *Transactions on Machine Learning Research*. https://arxiv.org/abs/2305.16307

> Considered as the back-translation model — SOTA for Indic, MIT-licensed — but the HuggingFace weights are gated and the IndicTransToolkit lagged transformers v5 at integration time. Documented as the preferred alternative to revisit against the gold set.

---

## Resource Level Classification

Joshi, P., Santy, S., Budhiraja, A., Bali, K., & Choudhury, M. (2020). The state and fate of linguistic diversity and inclusion in the NLP world. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics* (pp. 6282–6293). https://arxiv.org/abs/2004.09095

> Introduces a six-class taxonomy (Classes 0–5) for language resource levels in NLP. Provides baseline classification for all four languages in this study.

Ranathunga, S., Lee, E. A., Prifti Skenduli, M., Shekhar, R., Alam, M., & Kaur, R. (2023). Neural machine translation for low-resource languages: A survey. *ACM Computing Surveys*, 55(11), 1–37. https://arxiv.org/abs/2106.15115

> Reviews quantitative thresholds used in the literature to distinguish low-resource (<2B words) from mid-resource (2B–100B words) language corpora; contextualizes where Indic languages fall within this taxonomy.
