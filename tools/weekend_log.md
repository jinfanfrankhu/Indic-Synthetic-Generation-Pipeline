
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
