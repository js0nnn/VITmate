# 11 - Limitations and Future Work

These are the known limitations of the current system, stated plainly.

## Speech recognition

- **Depends on the browser.** VITmate uses the browser's built-in Web Speech API. It works best in Chrome and Edge, varies in Safari, isn't available in Firefox by default, and doesn't work in Brave, which has the API but no speech service. Other Chromium forks are detected at runtime. The compatibility banner and "Learn more" dialog tell users this, and Type mode always works.
- **Needs the browser vendor's online speech service.** In Chrome and Edge the audio is processed by the vendor's cloud service, not by VITmate, so voice input needs an internet connection and is subject to the vendor's privacy policy.
- **Pause tolerance is a fixed window.** After a finalised phrase the window is 1.2 s, and 2 s while a phrase is still interim. A speaker who pauses longer mid-sentence will submit early. They can speak again or use the stop button.
- **Recognition errors pass through.** If the browser mishears ("VTOP" → "v top"), the classifier sees the misheard text. The spoken-style challenge set measures robustness to such transcripts, but real accents and noise may be harder than hand-written examples.
- **A real-microphone end-to-end test can't be automated.** Tests use a simulated recogniser, and real use was checked manually.

## Knowledge base

- **Static snapshot (24 September 2026)**, not a live mirror of the VIT website. NIRF 2026, for example, wasn't published at collection time.
- **Some information isn't published officially and so isn't stated:** fee amounts, library hours, bus routes and timings, HOD names, dress code and college timings.
- **Source conflicts exist.** QS ranks couldn't be verified on topuniversities.com, and VIT's own pages disagree on the edition year. Patent counts differ between VIT's NIRF data and the IPR Cell list. These are disclosed in answers and documented in [09-knowledge-base.md](09-knowledge-base.md).
- **Placement statistics** come from two sources with different scopes (CDC: all campuses, offers; NIRF: Vellore graduates). Both are given with context, but they aren't directly comparable.

## Model and dataset

- **One intent per message.** "What are the fees and hostel rules?" gets an answer for the dominant intent only.
- **Weak intents remain.** `ffcs` (test F1 0.57: edge questions about minors, credits and branch change overlap programmes, syllabus and admissions), `greeting`/`goodbye` (0.70), `campus_facilities` (0.71), and `schools`/`vtop` (0.73). See [07-evaluation.md](07-evaluation.md).
- **The model choice is close.** DistilBERT and bge-small were within noise on validation. DistilBERT won on a reliability guardrail, while bge-small scored higher on the test set and is faster. Both are documented in [05-model-comparison.md](05-model-comparison.md).
- **Unsupported topics can still be misrouted with moderate confidence**, e.g. "what are the college timings" → sports (0.54).
- **The training data is partly authored**, not collected from real users. Real student queries would be more varied.
- **The small held-out sets give noisy estimates.** There are only 339 test queries, about 6–10 per intent, so per-intent F1 can swing by more than 0.1 from a single example. This is why model selection used the mean over seeds on validation.
- **Softmax confidence isn't calibrated probability, and the threshold is a safety floor.** On v2 the validation sweep favoured 0.0 (never abstain). The deployed 0.35 was kept deliberately so that VITmate still offers "did you mean" topics rather than guessing on unclear questions. Its measured cost is 0.0047 validation macro-F1.
- **Context is lightweight:** one current topic, pronoun rewriting and one level of follow-up detail. There's no long-term memory or entity tracking.

## Application

- **History is per browser and device.** It's stored in IndexedDB, isn't synchronised between devices, and is lost in private windows or when site data is cleared. There are no accounts, by design.
- **Not deployed yet.** Hosting needs HTTPS for the microphone to work.

## Future enhancements

1. Collect anonymised real queries (with consent) and use active learning on low-confidence questions.
2. Semi-automatic knowledge-base refresh with change detection on official pages, especially at NIRF and QS release times.
3. Multi-intent detection and entity extraction (a specific school, programme or campus).
4. An optional server-side or on-device speech-recognition fallback for browsers without the Web Speech API, with privacy review.
5. Optional browser text-to-speech for spoken replies.
6. Multilingual support (Tamil, Hindi, Telugu).
7. Confidence calibration (temperature scaling) and ONNX / INT8 export for smaller hosts.
8. Deployment with HTTPS on a free hosting tier.
