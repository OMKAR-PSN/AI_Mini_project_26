# Numeric annotation review

Reviewed four **development** scenes from the pinned dataset, without using held-out examples to tune anything. Image order in the local contact sheet `tmp/phase3a/numeric_annotation_review.png` follows these rows:

| Dataset row | Original answer | Question | Visual observation |
|---|---:|---|---|
| 174 | 15266 | How many residential buildings are there? | Dense mixed urban image. Individual residential buildings cannot be counted reliably at this display resolution. The exact label cannot be visually confirmed. |
| 1848 | 1675 | What is the number of rectangular buildings? | Urban and agricultural land coexist. Shape-specific individual building counts are not visually resolvable. |
| 1723 | 1111 | How many residential buildings are there? | Agricultural scene with settlement areas. Residential use and the exact count cannot be inferred reliably from this RGB patch. |
| 1405 | 966 | What is the amount of rectangular residential buildings? | Mixed settlement/agriculture. Exact shape-and-use count is not independently verifiable visually. |

All are 256×256 patches. These observations **do not establish that the labels are wrong**. Original RSVQA uses automatically generated questions/answers associated with geographic information; annotation semantics and geographic extent need examination against original metadata before correction. This subset exposes only image/question/answer, so its native geographic metadata and original object associations cannot be recovered here.

The ingestion audit flags 135 answers with absolute numeric value ≥100. All 2,000 labels remain unchanged; no numeric or difficult questions were removed. Exact match is still primary; numeric absolute error is a secondary diagnostic with parseability counts. The pilot's uniform question sample contains20 yes/no and10 numeric answers, **no categorical examples**. The whole subset contains1368 yes/no,603 numeric,29 categorical answers. A zero pilot category count is a coverage limitation, not a reported accuracy of0.

Full scene/question identities and original row indices are in each run's `annotation_review.csv` and `roster_all.csv`. This review does not authorize changing labels or tuning on the test partition.
