# 12 - Results Summary

All values are copied from [`results/`](results/). Details are in [05](05-model-comparison.md) (comparison) and [07](07-evaluation.md) (evaluation).

## Deployed model (v2)

**DistilBERT** fine-tuned for 38-intent classification (67.0M parameters, fp16 checkpoint in two shards, CPU).

| Measure | Value |
|---|---|
| Test accuracy / macro-F1 / weighted-F1 (n = 339) | **0.8496 / 0.8496 / 0.8499** |
| Test macro-F1 at the deployed threshold 0.35 | 0.8521 |
| Spoken-style accuracy / macro-F1 (n = 120, held out) | **0.9500 / 0.9533** |
| Out-of-scope recall (977 unseen CLINC150 queries, threshold 0.35) | **90.58%** (88.23% arg-max) |
| In-scope test questions not answered with an intent (these get "did you mean") | 6.18% |
| Median / p95 CPU latency per query | **12.78 ms** / 15.40 ms |
| Memory (fresh process, load + inference) | 683 MB RSS |
| Best epoch / validation macro-F1 | 5 / 0.8895 |
| Training time (CPU) | 405 s |

## Model selection

| Metric | DistilBERT | bge-small |
|---|---|---|
| Validation macro-F1 @0.35, 3 seeds (**primary**) | 0.8941 ± 0.0086 | 0.8899 ± 0.0092 |
| Validation OOS recall @0.35 (**guardrail**) | 0.9271 ± 0.0451 | 0.9010 ± 0.0548 |
| Test macro-F1 @0.35 (reported only) | 0.8675 ± 0.0138 | 0.8831 ± 0.0077 |
| Spoken macro-F1 @0.35 (reported only) | 0.9701 ± 0.0135 | 0.9711 ± 0.0101 |
| Median latency | 12.7 ms | 7.9 ms |

The primary gap was within noise, so the validation OOS guardrail decided in favour of **DistilBERT**. All five candidates beat the TF-IDF baseline (validation macro-F1 0.8028).

![Finalist comparison](graphs/final_comparison.png)

![Macro-F1 by model](graphs/model_comparison_macro_f1.png)

## Development history in numbers

| Version | Deployed model | Intents | Test macro-F1 | Spoken macro-F1 | OOS recall |
|---|---|---|---|---|---|
| v1 | bge-small (33.4M) | 36 | 0.8490 (n = 319) | 0.9552 (n = 113) | 89.93% (n = 983) |
| **v2** | **DistilBERT (67.0M)** | **38** | **0.8496** (n = 339) | **0.9533** (n = 120) | **90.58%** (n = 977) |

The v1 and v2 test sets differ, so these rows describe the deployed systems, not a controlled model comparison.

![v1 vs v2](graphs/v1_vs_v2_final_model.png)

## Behaviour improvements in v2

- **Speech:** natural pauses no longer cut questions short (continuous recognition with a 1.2 s / 2 s silence window).
- **Broad questions:** "is VIT good" gets a factual overview (v1: "please rephrase").
- **New topics:** patents and research, and rankings (NIRF 2025, THE 2026, QS as reported by VIT, NAAC), all with their years.
- **Unclear questions:** VITmate offers "did you mean" topics instead of a dead end.
- **Corrected claims:** ABET accreditation and Institution-of-Eminence claims that authoritative sources don't support were corrected.
- **History:** stored in IndexedDB (survives restarts, safe with several tabs), with automatic migration of v1 chats.

## Graphs

| Graph | Shows |
|---|---|
| [final_comparison.png](graphs/final_comparison.png) | Finalists at the deployed threshold, with resources |
| [model_comparison_macro_f1.png](graphs/model_comparison_macro_f1.png), [model_comparison_accuracy.png](graphs/model_comparison_accuracy.png) | All candidates on validation / test / spoken-style |
| [accuracy_vs_latency.png](graphs/accuracy_vs_latency.png), [model_efficiency.png](graphs/model_efficiency.png) | Speed, size and parameter trade-offs |
| [training_curve.png](graphs/training_curve.png) | Loss and validation metrics per epoch (deployed model) |
| [per_intent_f1.png](graphs/per_intent_f1.png), [confusion_matrix.png](graphs/confusion_matrix.png) | Per-intent quality |
| [out_of_scope_and_threshold.png](graphs/out_of_scope_and_threshold.png) | OOS recall and threshold sweep |
| [dataset_distribution.png](graphs/dataset_distribution.png), [dataset_sources.png](graphs/dataset_sources.png) | Dataset v2 composition |
| [v1_vs_v2_final_model.png](graphs/v1_vs_v2_final_model.png) | Deployed model, v1 vs v2 |

## Conclusion

VITmate demonstrates a complete voice-enabled chatbot pipeline: browser speech recognition, a fine-tuned transformer intent classifier, and a grounded, source-cited knowledge base behind a polished chat interface. Separating intent recognition from factual content kept answers accurate and easy to correct; in v2, two unsupported claims were fixed without any retraining. Measuring several architectures across multiple seeds, and selecting on validation data with explicit reliability guardrails, means the model choice rests on evidence rather than assumption, and the documentation records where that evidence was close. The system runs on a CPU and is structured for straightforward online deployment.
