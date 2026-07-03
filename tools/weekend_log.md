
## 2026-07-02_1258
```n(back-translation skipped)[judge] day=2026-07-02: 6 attempts, 1 scored in 22s; quota used 18/900; overall mean=1.000 median=1.000
== structural (fail/total by task) ==
  classification   1/160
  instruction      0/160
  qa               0/160
  reasoning        0/160
  summarization    0/160
  translation      57/160
  examples:
    syn-hi-translation-004-003: expected duplicates prompt (no-op generation)
    syn-hi-translation-004-007: expected duplicates prompt (no-op generation)
    syn-hi-translation-bs-0007-010: translation item missing 'expected' answer
    syn-hi-translation-bs-0009-012: translation item missing 'expected' answer
    syn-hi-translation-bs-0012-015: expected duplicates prompt (no-op generation)
    syn-hi-translation-bs-0013-016: expected duplicates prompt (no-op generation)
    syn-hi-translation-bs-0016-019: expected duplicates prompt (no-op generation)
    syn-hi-translation-bs-0017-020: expected duplicates prompt (no-op generation)

== back-translation (69 scored / 960 items, 69 with cosine) ==
  overall: mean=0.822 median=0.865 min=0.209 p10=0.630 max=0.984
  by lang/task (mean cosine, n):
    hi/classification   0.865  (n=40)
    hi/instruction      0.763  (n=29)
  LOW cosine (<0.5): 3 � review candidates
    syn-hi-instruction-005-004 cos=0.4097
    syn-hi-instruction-bs-0007-011 cos=0.4366
    syn-hi-instruction-bs-0019-023 cos=0.2092
  unscored remaining (back-translation): 891

== judge ensemble (5 judge-scores) ==
  coverage by judge: {'nemotron-3-super-120b-a12b:free': 3, 'gpt-oss-20b:free': 2}
  fluency      mean=0.970 min=0.950
  faithfulness mean=0.990 min=0.950
  bias         mean=1.000 min=1.000
  overall      mean=0.987 min=0.967
  ensemble-mean overall: 0.989; items with ensemble<0.6: 0 (review candidates)
```

## 2026-07-03_0900
```n[bt] loading NLLB-200 + SBERT (first run downloads the model)...
python.exe : Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher 
rate limits and faster downloads.
At C:\repos\Indic\tools\weekend_run.ps1:25 char:15
+ ... se { $bt = (& $py tools\score_backtranslation.py --include-translatio ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (Warning: You ar...ster downloads.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 

Loading weights:   0%|          | 0/1016 [00:00<?, ?it/s]
Loading weights: 100%|##########| 1016/1016 [00:00<00:00, 25435.65it/s]

Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]
Loading weights: 100%|##########| 199/199 [00:00<00:00, 5926.60it/s]
[bt] 50/103  (0.12/s)  cos_mean=0.890
[bt] 100/103  (0.12/s)  cos_mean=0.896
[bt] done: 103 scored in 865s; cosine mean=0.895 median=0.915 min=0.587
[judge] 25 attempts, 17 ok (8 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 50 attempts, 39 ok (11 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 75 attempts, 64 ok (11 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 100 attempts, 89 ok (11 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 125 attempts, 113 ok (12 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 150 attempts, 136 ok (14 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 175 attempts, 159 ok (16 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 200 attempts, 184 ok (16 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 225 attempts, 208 ok (17 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 250 attempts, 232 ok (18 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 275 attempts, 256 ok (19 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 300 attempts, 280 ok (20 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 325 attempts, 303 ok (22 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 350 attempts, 324 ok (26 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 375 attempts, 348 ok (27 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 400 attempts, 369 ok (31 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 425 attempts, 391 ok (34 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 450 attempts, 413 ok (37 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] day=2026-07-03: 450 attempts, 413 scored in 4225s; quota used 450/900; overall mean=0.955 median=0.967
[judge] congested this run (retry next): ['openrouter:meta-llama/llama-3.3-70b-instruct:free', 'openrouter:qwen/qwen3-next-80b-a3b-instruct:free']
== structural (fail/total by task) ==
  classification   1/160
  instruction      0/160
  qa               0/160
  reasoning        0/160
  summarization    0/160
  translation      0/103
  examples:
    syn-ur-classification-bs-0007-011: possible truncation (no terminal punctuation)

== back-translation (903 scored / 903 items, 903 with cosine) ==
  overall: mean=0.868 median=0.902 min=0.059 p10=0.730 max=1.000
  by lang/task (mean cosine, n):
    hi/classification   0.865  (n=40)
    hi/instruction      0.764  (n=40)
    hi/qa               0.942  (n=40)
    hi/reasoning        0.928  (n=40)
    hi/summarization    0.933  (n=40)
    hi/translation      0.897  (n=25)
    ml/classification   0.822  (n=40)
    ml/instruction      0.755  (n=40)
    ml/qa               0.931  (n=40)
    ml/reasoning        0.886  (n=40)
    ml/summarization    0.895  (n=40)
    ml/translation      0.886  (n=28)
    ta/classification   0.779  (n=40)
    ta/instruction      0.768  (n=40)
    ta/qa               0.938  (n=40)
    ta/reasoning        0.855  (n=40)
    ta/summarization    0.891  (n=40)
    ta/translation      0.897  (n=22)
    ur/classification   0.829  (n=40)
    ur/instruction      0.776  (n=40)
    ur/qa               0.930  (n=40)
    ur/reasoning        0.886  (n=40)
    ur/summarization    0.923  (n=40)
    ur/translation      0.903  (n=28)
  LOW cosine (<0.5): 17 ù review candidates
    syn-hi-instruction-005-004 cos=0.4097
    syn-hi-instruction-bs-0007-011 cos=0.4366
    syn-hi-instruction-bs-0019-023 cos=0.2092
    syn-ml-classification-bs-0010-014 cos=0.4237
    syn-ml-instruction-bs-0005-009 cos=0.2887
    syn-ml-instruction-bs-0007-011 cos=0.414
    syn-ml-instruction-bs-0009-013 cos=0.4438
    syn-ml-summarization-bs-0009-028 cos=0.4983
    syn-ta-classification-005-004 cos=0.3357
    syn-ta-classification-bs-0015-019 cos=0.1439
  unscored remaining (back-translation): 0

== judge ensemble (418 judge-scores) ==
  coverage by judge: {'nemotron-3-super-120b-a12b:free': 198, 'gpt-oss-20b:free': 220}
  fluency      mean=0.927 min=0.300
  faithfulness mean=0.957 min=0.000
  bias         mean=0.982 min=0.700
  overall      mean=0.955 min=0.667
  ensemble-mean overall: 0.955; items with ensemble<0.6: 0 (review candidates)
```

## 2026-07-03_1500
```n[bt] all applicable items already scored (903 on file); nothing to do.
[judge] 25 attempts, 11 ok (14 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 50 attempts, 31 ok (19 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 75 attempts, 54 ok (21 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 100 attempts, 77 ok (23 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 125 attempts, 100 ok (25 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 150 attempts, 122 ok (28 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 175 attempts, 145 ok (30 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 200 attempts, 166 ok (34 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 225 attempts, 190 ok (35 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 250 attempts, 215 ok (35 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 275 attempts, 239 ok (36 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 300 attempts, 260 ok (40 fail); congested=['llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 325 attempts, 280 ok (45 fail); congested=['gpt-oss-20b:free', 'llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] 350 attempts, 299 ok (51 fail); congested=['gpt-oss-20b:free', 'llama-3.3-70b-instruct:free', 'qwen3-next-80b-a3b-instruct:free']
[judge] day=2026-07-03: 365 attempts, 305 scored in 3937s; quota used 815/900; overall mean=0.932 median=0.967
[judge] congested this run (retry next): ['openrouter:meta-llama/llama-3.3-70b-instruct:free', 'openrouter:nvidia/nemotron-3-super-120b-a12b:free', 'openrouter:openai/gpt-oss-20b:free', 'openrouter:qwen/qwen3-next-80b-a3b-instruct:free']
== structural (fail/total by task) ==
  classification   1/160
  instruction      0/160
  qa               0/160
  reasoning        0/160
  summarization    0/160
  translation      0/103
  examples:
    syn-ur-classification-bs-0007-011: possible truncation (no terminal punctuation)

== back-translation (903 scored / 903 items, 903 with cosine) ==
  overall: mean=0.868 median=0.902 min=0.059 p10=0.730 max=1.000
  by lang/task (mean cosine, n):
    hi/classification   0.865  (n=40)
    hi/instruction      0.764  (n=40)
    hi/qa               0.942  (n=40)
    hi/reasoning        0.928  (n=40)
    hi/summarization    0.933  (n=40)
    hi/translation      0.897  (n=25)
    ml/classification   0.822  (n=40)
    ml/instruction      0.755  (n=40)
    ml/qa               0.931  (n=40)
    ml/reasoning        0.886  (n=40)
    ml/summarization    0.895  (n=40)
    ml/translation      0.886  (n=28)
    ta/classification   0.779  (n=40)
    ta/instruction      0.768  (n=40)
    ta/qa               0.938  (n=40)
    ta/reasoning        0.855  (n=40)
    ta/summarization    0.891  (n=40)
    ta/translation      0.897  (n=22)
    ur/classification   0.829  (n=40)
    ur/instruction      0.776  (n=40)
    ur/qa               0.930  (n=40)
    ur/reasoning        0.886  (n=40)
    ur/summarization    0.923  (n=40)
    ur/translation      0.903  (n=28)
  LOW cosine (<0.5): 17 ù review candidates
    syn-hi-instruction-005-004 cos=0.4097
    syn-hi-instruction-bs-0007-011 cos=0.4366
    syn-hi-instruction-bs-0019-023 cos=0.2092
    syn-ml-classification-bs-0010-014 cos=0.4237
    syn-ml-instruction-bs-0005-009 cos=0.2887
    syn-ml-instruction-bs-0007-011 cos=0.414
    syn-ml-instruction-bs-0009-013 cos=0.4438
    syn-ml-summarization-bs-0009-028 cos=0.4983
    syn-ta-classification-005-004 cos=0.3357
    syn-ta-classification-bs-0015-019 cos=0.1439
  unscored remaining (back-translation): 0

== judge ensemble (723 judge-scores) ==
  coverage by judge: {'nemotron-3-super-120b-a12b:free': 373, 'gpt-oss-20b:free': 350}
  fluency      mean=0.914 min=0.000
  faithfulness mean=0.944 min=0.000
  bias         mean=0.978 min=0.400
  overall      mean=0.945 min=0.233
  ensemble-mean overall: 0.942; items with ensemble<0.6: 4 (review candidates)
    syn-ml-instruction-bs-0010-014
    syn-ml-instruction-bs-0026-030
    syn-ml-qa-bs-0027-031
    syn-ml-summarization-bs-0012-015
```
