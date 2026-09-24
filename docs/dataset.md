# VITmate Intent Dataset

The VITmate dataset is **not** an untouched public dataset. An existing university chatbot dataset was used as the **foundation** and was **adapted and extended** for a VIT-specific assistant. Out-of-domain data came from a public intent benchmark.

Build it with `python -m training.build_dataset`. The output goes to `data/processed/`, and statistics to `data/processed/dataset_report.json`.

## Sources

| Source | Licence | How it is used | Examples in final pool |
|---|---|---|---|
| **University Chatbot Dataset** by Tushar Paul (Kaggle: `tusharpaul2001/university-chatbot-dataset`; also distributed by GTS at gts.ai). File `data/raw/university_chatbot_intents.json` | Apache 2.0 | Foundation: 39 intents / 412 patterns, remapped to the VITmate taxonomy, with VIT substituted for the generic "UNI" placeholders | 344 |
| **Authored VITmate utterances** (`data/authored/*.yaml`) | Project data | New VIT-specific intents (FFCS, VITEEE, VTOP, ...) and paraphrases in varied styles: short and long, formal and casual, Indian-English, and speech-like transcripts with fillers ("uh", "um") and no punctuation | 1,326 |
| **CLINC150** (Larson et al., 2019, "An Evaluation Dataset for Intent Classification and Out-of-Scope Prediction"). File `data/raw/clinc150_data_full.json` | CC BY 3.0 | (a) up to 30 extra paraphrases each for greeting, goodbye, thanks, bot identity and capabilities; (b) its dedicated out-of-scope queries plus one query from each unrelated domain (banking, travel, cooking, ...) as `out_of_scope` examples; (c) its **held-out out-of-scope test split** as a separate OOS evaluation | 449 |

**Use of AI assistance.** The authored utterances were written with the help of an AI coding assistant during development and then reviewed. VITmate itself does **not** use any external LLM at runtime.

## Analysis of the original dataset

| Observation | Consequence |
|---|---|
| 39 intents, only 3–27 patterns each (412 total) | Too small to fine-tune reliably, so it was extended |
| Many responses are placeholders ("NUMBER", "LINK", "XYZ is college principal") or describe another college ("2 floors", a Gujarati canteen menu) | **All responses were discarded**; answers come from the VIT knowledge base |
| Overlapping tags (`hod`/`ithod`/`computerhod`/`extchod`; `sem`/`vacation`/`Mess Timetable`) | Merged |
| Bare keywords ("it", "k", "call") and corrupted text ("??? ??? ??") | Removed through pattern overrides |
| No out-of-scope examples | `out_of_scope` class built from CLINC150 and authored queries |

## Mapping to the VITmate taxonomy (36 intents)

Defined in [`data/taxonomy.yaml`](../data/taxonomy.yaml).

| Action | Original tags → VITmate intent |
|---|---|
| **Kept** | greeting, goodbye, hostel, library, sports, placement → placements, scholarship → scholarships, syllabus |
| **Adapted / renamed** | salutaion → thanks · task → capabilities · swear → profanity · location → campus_location · number → contact_info · course → programmes · sem → examinations · vacation → academic_calendar · event + committee → clubs_events · ragging → anti_ragging · fees → fees (hostel-fee patterns moved here) |
| **Merged** | name + creator → bot_identity · admission + document → admissions · canteen + menu → dining · facilities + infrastructure + floors → campus_facilities · hod + ithod + computerhod + extchod → faculty · principal → about_vit · random → out_of_scope |
| **Split** | `Mess Timetable` patterns reassigned to dining, transport and academic_calendar |
| **Removed** | `hours`, `uniform` and `college intake`, because no official VIT information could be verified for them (answering would mean inventing timings, dress codes or seat counts) |
| **New VIT-specific intents** | ffcs, schools, attendance, viteee, health_services, transport, vtop, student_welfare, grievances, internships |

## Cleaning and leakage prevention

1. Unicode NFKC normalisation and whitespace collapsing; casing is kept because the tokenizer is uncased anyway.
2. **Exact-duplicate removal** on a lower-cased, punctuation-free key.
3. **Label-conflict removal**: a text that appears under two intents is dropped entirely (none remained).
4. **Near-duplicate grouping**: utterances with the same content words, ignoring fillers such as "uh", "please", "can you tell me", are kept together in one split, so paraphrase pairs like "What is FFCS?" and "Can you tell me what FFCS is?" can't sit on both sides of a split.
5. **Stratified 70 / 15 / 15 split per intent** (seed 42).
6. **Held-out protection**: any pool utterance that duplicates or near-duplicates a held-out challenge query is removed from the pool (40 removed).
7. An assertion in `build_dataset.py` and `tests/test_dataset.py` verifies that no text appears in both train and val/test.

## Final dataset

| Split | Examples | Purpose |
|---|---|---|
| Train | 1,478 | Model fitting |
| Validation | 322 | Early stopping, model selection, confidence-threshold selection |
| Test | 319 | Final reported metrics (never used for any decision) |
| Spoken-style challenge | 113 | Hand-written, held out: imitates browser speech-recognition transcripts ("uh what are the hostel facilities at VIT") |
| OOS evaluation | 983 | CLINC150 `oos_test` queries (minus any mentioning campus words): measures out-of-scope recall |

Total labelled pool: **2,119** examples (train + val + test).

### Per-intent counts

| Intent | Train | Val | Test | Total |
|---|---|---|---|---|
| `greeting` | 42 | 9 | 9 | 60 |
| `goodbye` | 43 | 9 | 10 | 62 |
| `thanks` | 42 | 9 | 9 | 60 |
| `bot_identity` | 54 | 11 | 11 | 76 |
| `capabilities` | 35 | 8 | 8 | 51 |
| `profanity` | 16 | 4 | 4 | 24 |
| `out_of_scope` | 301 | 64 | 64 | 429 |
| `about_vit` | 33 | 7 | 7 | 47 |
| `campus_location` | 29 | 9 | 7 | 45 |
| `contact_info` | 31 | 6 | 6 | 43 |
| `ffcs` | 39 | 8 | 8 | 55 |
| `programmes` | 45 | 10 | 10 | 65 |
| `schools` | 27 | 6 | 6 | 39 |
| `faculty` | 31 | 7 | 7 | 45 |
| `syllabus` | 26 | 6 | 6 | 38 |
| `examinations` | 35 | 8 | 8 | 51 |
| `academic_calendar` | 33 | 7 | 7 | 47 |
| `attendance` | 28 | 6 | 6 | 40 |
| `admissions` | 39 | 8 | 8 | 55 |
| `viteee` | 35 | 7 | 7 | 49 |
| `fees` | 38 | 8 | 9 | 55 |
| `scholarships` | 39 | 9 | 9 | 57 |
| `hostel` | 39 | 9 | 9 | 57 |
| `dining` | 38 | 8 | 8 | 54 |
| `library` | 32 | 7 | 7 | 46 |
| `sports` | 31 | 6 | 6 | 43 |
| `health_services` | 28 | 6 | 6 | 40 |
| `transport` | 28 | 6 | 6 | 40 |
| `campus_facilities` | 34 | 7 | 7 | 48 |
| `clubs_events` | 31 | 11 | 8 | 50 |
| `vtop` | 28 | 6 | 6 | 40 |
| `student_welfare` | 28 | 6 | 6 | 40 |
| `anti_ragging` | 30 | 6 | 6 | 42 |
| `grievances` | 26 | 5 | 5 | 36 |
| `placements` | 35 | 7 | 7 | 49 |
| `internships` | 29 | 6 | 6 | 41 |

**Class balance.** VIT intents have 36–76 examples each. `out_of_scope` is intentionally larger (429) because it has to cover an open-ended space of unrelated questions. Training uses inverse-square-root class weights so that this class doesn't dominate the loss.

## Robustness iteration

After the first models were trained, probing with edge cases showed confident misclassifications:

- keyboard gibberish such as "asdf" → `examinations`
- other universities such as "tell me about IIT Madras" → `about_vit`
- branch-change questions → `syllabus`

A third authored batch, [`data/authored/robustness.yaml`](../data/authored/robustness.yaml) with 53 utterances, was added to cover these cases, and **all** candidate models were retrained and re-compared. The held-out test sets were not changed.
