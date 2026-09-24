# Lab Report Material — VITmate

**Title:** VITmate: A Voice-Enabled Deep Learning-Based Campus Assistant for VIT
**Author:** B. Jaison Edward (Reg. No. 23BAI0094)

This document collects material for the lab report. All numbers come from the scripts in `training/`; the raw outputs are in `docs/results/`.

---

## 1. Introduction

Students at VIT often need quick answers about academic rules (FFCS, attendance, CAT/FAT), campus services (hostels, mess, library, health centre), admissions (VITEEE, scholarships) and careers (placements, internships). This information is spread across many pages of the official website and PDF regulations. **VITmate** is a conversational assistant that accepts **spoken or typed** questions, identifies the user's intent with a **deep-learning classifier**, and answers from a curated knowledge base of **official VIT information**.

## 2. Problem Statement

Develop and deploy an online voice-enabled chatbot that:

- converts speech to text with a suitable speech-recognition technique
- understands the text with a deep-learning intent-classification model
- returns an appropriate response
- displays both the recognised speech and the response

For a university assistant, the answers must also be **factually grounded**. The system must not invent fees, dates or policies, and it must recognise questions outside its scope.

## 3. Objectives

1. Build a VIT-specific intent dataset by adapting an existing university chatbot dataset.
2. Train and compare deep-learning intent classifiers, and select one by measured validation performance.
3. Separate intent recognition (the neural network) from factual answers (the knowledge base).
4. Integrate browser-based speech recognition so users need no installation.
5. Handle out-of-scope and low-confidence inputs safely.
6. Provide a polished, responsive, accessible chat interface with conversation history and themes.
7. Evaluate the system with standard metrics: accuracy, precision, recall, macro/weighted F1, a confusion matrix, OOS recall, latency and memory.

## 4. Dataset

See [dataset.md](dataset.md) for full details.

- **Foundation:** the University Chatbot Dataset (Tushar Paul, Kaggle; Apache 2.0), with 39 intents and 412 patterns.
- **Extension:** 1,326 authored VIT-specific utterances, plus CLINC150 (CC BY 3.0) data for out-of-scope examples and chit-chat paraphrases.
- **Final dataset:** 36 intents and 2,119 labelled examples, split 1,478 / 322 / 319 (train / validation / test).
- **Held-out sets:** 113 spoken-style queries and 983 CLINC150 out-of-scope queries.

## 5. Data Preprocessing

1. Remapping original tags to the new taxonomy (kept / merged / split / removed), with pattern-level overrides.
2. Replacing the dataset's university placeholders ("UNI") with "VIT", and dropping corrupted or keyword-only patterns.
3. Unicode NFKC normalisation and whitespace normalisation.
4. Exact de-duplication, and removal of texts carrying conflicting labels.
5. Near-duplicate grouping (a content-word signature that ignores fillers), then a stratified 70/15/15 split by group, so paraphrase pairs never cross splits.
6. Removal of any pool utterance that overlaps the held-out challenge sets.
7. Tokenisation with the model's WordPiece tokenizer (uncased, max 64 tokens, dynamic padding).

## 6. Model Architecture

The final model, **`BAAI/bge-small-en-v1.5`**, is a BERT-style Transformer encoder:

- 12 layers, hidden size 384, 12 attention heads, about 33M parameters
- pre-trained for English sentence representations
- a linear classification layer over the `[CLS]` token representation (384 → 36 intents) added on top

```text
Input text ──► WordPiece tokenizer ──► [CLS] tok1 … tokN [SEP]
          ──► 12 × Transformer encoder layers (self-attention + feed-forward)
          ──► [CLS] vector (384-d) ──► Dropout ──► Linear(384 → 36) ──► Softmax
          ──► intent + confidence
```

Candidates compared (same data and training procedure):

| Candidate | Type | Parameters |
|---|---|---|
| TF-IDF (word 1–2-grams + char 2–5-grams) + Logistic Regression | classical baseline | – |
| `google/bert_uncased_L-4_H-256_A-4` (BERT-mini) | Transformer, 4 layers | 11M |
| `sentence-transformers/all-MiniLM-L6-v2` | Transformer, 6 layers | 23M |
| `BAAI/bge-small-en-v1.5` | Transformer, 12 layers | 33M |
| `distilbert-base-uncased` | Transformer, 6 layers | 67M |

## 7. Training Methodology

- **Loss:** cross-entropy with inverse-square-root class-frequency weights, which reduce the influence of the large `out_of_scope` class.
- **Optimiser:** AdamW (weight decay 0.01) with gradient clipping at 1.0. Learning rates per candidate: 1e-4 for MiniLM and bge-small, 5e-5 for DistilBERT, 2e-4 for BERT-mini.
- **Schedule:** linear decay with 10% warm-up; batch size 16.
- **Early stopping:** on validation macro-F1 with patience 4 (maximum 25 epochs). The best checkpoint is restored.
- **Model selection:** by mean validation macro-F1 across seeds; the test set is never used for decisions.
- **Confidence threshold:** chosen by a sweep on the validation set, with low-confidence predictions mapped to out-of-scope.
- **Hardware:** CPU only (no GPU).

## 8. Speech Recognition Method

See [speech_recognition.md](speech_recognition.md). VITmate uses the **Web Speech API** built into the browser:

- a `SpeechRecognition` object with `lang = "en-IN"` and interim results
- the final transcript goes into the same pipeline as typed text
- only text reaches the VITmate server
- permission, no-microphone, silence, network and unsupported-browser cases each have their own message

This satisfies the "no installation" requirement and moves speech-to-text load off the server.

## 9. Knowledge Base

See [knowledge_base.md](knowledge_base.md). The knowledge base is a YAML file with one entry per intent:

- summary, follow-up details, official source URLs, a time-sensitivity flag and a verification date
- collected from official VIT pages on 24 September 2026
- volatile facts (fee amounts, placement statistics) are linked rather than stated
- editable without retraining

## 10. System Architecture

See [architecture.md](architecture.md) for the flowchart and sequence diagrams. In brief:

```text
Browser (Type / Speak) → Web Speech API → FastAPI /api/chat → Transformer intent classifier
→ Response engine (threshold, context, fallbacks) + VIT knowledge base → Chat UI + localStorage history
```

## 11. Frontend Design

- React 18 + TypeScript + Vite; a ChatGPT-inspired layout that doesn't copy any brand.
- **Sidebar:** New Chat button; history grouped as Today / Yesterday / Previous 7 Days / Older; restore and delete (with confirmation); collapses to a drawer on small screens.
- **Chat:** user bubbles on the right, assistant replies with an avatar, safe Markdown rendering (no raw HTML), official-source links, and an intent/confidence chip.
- **Input:** an animated **Type / Speak** segmented control. Type mode has an auto-growing textarea (Enter sends, Shift+Enter adds a new line). Speak mode has a microphone button with pulsing rings, a waveform, a live transcript and clear status and error messages.
- Typing indicator, auto-scroll, light/dark theme (system default, remembered), About dialog with a focus trap.
- Accessibility: semantic landmarks, ARIA labels, visible focus rings, keyboard-operable controls and reduced-motion support.

## 12. Backend Design

- FastAPI endpoints: `GET /api/health`, `GET /api/suggestions`, `POST /api/chat`.
- The model and knowledge base are loaded **once** at startup (lifespan hook). If loading fails, the API reports "degraded" status instead of crashing.
- Input validation: message length 1–500 characters with control characters stripped, `input_mode` restricted to text or voice, and unknown context intents ignored.
- Errors return friendly JSON messages, never stack traces or file paths. CORS is restricted to configured origins, and the API docs are disabled in production.
- **Stateless context:** the client echoes `{previous_intent, depth}`. Pronoun follow-ups are rewritten with the topic title and re-classified; if the topic can't be confirmed, VITmate asks the user to clarify.

## 13. Results

All numbers below were produced by `python -m training.evaluate` on the deployed model (`backend/trained_model/`, fp16 weights, CPU). Raw outputs are in [docs/results/](results/).

### Final model: bge-small (best epoch 6, validation macro-F1 0.8923)

| Evaluation set | Accuracy | Macro precision | Macro recall | Macro F1 | Weighted F1 |
|---|---|---|---|---|---|
| **Test** (n=319, 36 intents) | 0.8589 | 0.8569 | 0.8603 | **0.8490** | 0.8573 |
| Test, with confidence threshold 0.35 | 0.8589 | 0.8809 | 0.8573 | 0.8596 | 0.8556 |
| **Spoken-style challenge** (n=113, held out) | 0.9558 | 0.9630 | 0.9560 | **0.9552** | 0.9550 |

- **Out-of-scope recall** on 983 unseen CLINC150 out-of-scope queries: **89.9%** with the threshold (85.0% from arg-max alone).
- **Confidence threshold** 0.35, chosen by a sweep on the validation set: 5.1% of in-scope test questions are answered with "please rephrase" instead of a possibly wrong answer.
- **CPU efficiency:** model load 0.15 s (warm file cache); single-query latency median **8.02 ms** (p95 9.17 ms); process memory 684 MB RSS; model size 67.7 MB.
- The weakest intents are `campus_facilities` and `academic_calendar`. They are broad and overlap with dining, transport and clubs. The confusion matrix and all misclassified test examples are in [docs/results/evaluation.md](results/evaluation.md).

![Confusion matrix](results/confusion_matrix.png)

### Model comparison

Same splits and training procedure for every model. Selection used **validation macro-F1 only** (mean over 3 seeds for the two finalists).

| Candidate | Seeds | Params (M) | Size fp32 (MB) | Val macro-F1 | Test accuracy | Test macro-F1 | Test weighted-F1 | Spoken accuracy | Spoken macro-F1 | Latency (ms) | Train (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline (`TF-IDF (word+char) + Logistic Regression`) | 1 | - | - | 0.8022 | 0.8150 | 0.8178 | 0.8132 | 0.9292 | 0.9274 | 1.08 | 5 |
| bert-mini (`google/bert_uncased_L-4_H-256_A-4`) | 1 | 11.2 | 45.7 | 0.8311 | 0.8245 | 0.8288 | 0.8223 | 0.9558 | 0.9571 | 2.0 | 134 |
| minilm-l6 (`sentence-transformers/all-MiniLM-L6-v2`) | 3 | 22.7 | 91.9 | 0.8741 ± 0.0058 | 0.8809 ± 0.0000 | 0.8820 ± 0.0029 | 0.8757 ± 0.0020 | 0.9558 ± 0.0000 | 0.9557 ± 0.0014 | 4.23 | 190 |
| bge-small (`BAAI/bge-small-en-v1.5`) | 3 | 33.4 | 134.5 | 0.8943 ± 0.0098 | 0.8735 ± 0.0178 | 0.8661 ± 0.0187 | 0.8709 ± 0.0169 | 0.9646 ± 0.0089 | 0.9655 ± 0.0098 | 7.76 | 297 |
| distilbert (`distilbert-base-uncased`) | 1 | 67.0 | 268.9 | 0.8790 | 0.8777 | 0.8654 | 0.8736 | 0.9558 | 0.9584 | 12.75 | 604 |

**Why bge-small?** It had the highest mean validation macro-F1 (the pre-set criterion) and the best spoken-style scores, with an 8 ms CPU latency. MiniLM-L6 scored slightly higher on the test set (0.882 vs 0.866 ± 0.019), but that difference is within bge-small's seed variance, and choosing by test score would leak the test set into model selection. MiniLM-L6 is a sound alternative for hosts with very limited memory. Every transformer beat the TF-IDF baseline, and the largest model (DistilBERT, 67M parameters) was **not** the best, so a larger model wasn't justified.

## 14. Evaluation Metrics

- **Accuracy:** fraction of correctly classified queries.
- **Precision / Recall / F1 per intent:** precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = their harmonic mean.
- **Macro-averaged F1:** the unweighted mean over intents. It treats small intents as equally important, which makes it the primary selection metric.
- **Weighted F1:** the mean weighted by support.
- **Confusion matrix:** shows which intents are confused with which.
- **Out-of-scope recall:** the fraction of held-out unrelated queries that are correctly refused.
- **In-scope rejection rate:** the fraction of valid VIT questions refused as low-confidence (the cost of the threshold).
- **Efficiency:** model load time, single-query latency (median / p95) and process memory, all on CPU.

## 15. Limitations

- The knowledge base is a static snapshot and needs periodic manual updates.
- One intent per query; no multi-intent handling.
- Lightweight context (a single topic and one follow-up level).
- Part of the training data is authored rather than collected from real users.
- Voice input depends on browser support and on the vendor's online speech service.
- Topics without verifiable official information (college timings, dress code, bus routes) can't be answered in detail.

## 16. Future Enhancements

- Collect anonymised real queries (with consent) to improve the dataset, and use active learning on low-confidence queries.
- Semi-automatic knowledge-base refresh with change detection on official pages.
- Multi-intent detection and entity extraction (for example, a specific school or programme).
- Optional browser text-to-speech for spoken replies.
- Multilingual support (Tamil, Hindi, Telugu).
- ONNX or quantised INT8 inference for smaller hosting footprints.
- Deployment with HTTPS on a free hosting tier.

## 17. Conclusion

VITmate shows a complete voice-enabled chatbot pipeline: browser speech recognition → a fine-tuned transformer intent classifier → a grounded knowledge base → a polished chat interface. Separating intent recognition from factual content keeps answers accurate and easy to update. Measuring several architectures made it possible to justify the choice of model with numbers rather than assumptions. The system runs entirely on CPU and is structured for straightforward online deployment.
