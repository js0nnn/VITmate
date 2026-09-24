# VIT Knowledge Base

File: [`data/knowledge/vit_knowledge.yaml`](../data/knowledge/vit_knowledge.yaml)

The intent classifier decides **what** the user is asking about. The knowledge base provides **what VITmate answers**. The neural network never memorises VIT facts, so answers can be corrected or updated by editing one YAML file, with no retraining.

## How the information was collected

1. Relevant **official** pages were identified for each intent on `vit.ac.in`, `viteee.vit.ac.in` and `vtop.vit.ac.in`. They include the about, leadership, FFCS, programmes, schools, admissions, scholarships, library, hostels, sports, health services, counselling, anti-ragging, grievance, CDC/placement and contact pages, plus the official *FFCS Academic Regulations (v4.0)* PDF.
2. Only those pages were read; the site was **not** bulk-scraped. Navigation, banners and other boilerplate were discarded.
3. Facts were normalised into short summaries plus follow-up details. Research notes with per-topic sources are kept in `data/raw/vit_research_notes.json`.
4. Everything was retrieved on **24 September 2026**.

## What was deliberately *not* included

To avoid giving users wrong information, the knowledge base does **not** state:

- **Fee amounts.** They change every year and depend on fee category, so VITmate links to the official fee pages instead.
- **Placement statistics** (average or highest packages). The official figures found had no year attached. VITmate points to the official live placement tracker.
- **Library opening hours and fines.** The official page says they are shown on the library's display boards.
- **Bus routes and timings.** They are not published on the pages reviewed.
- **Names of individual HODs and deans.** They change often; VITmate points to the official faculty directory.
- **Travel directions and distances.** No official source was found.

If a user asks for these, VITmate says what it does know and where the official, current information is published.

## Entry format

```yaml
entries:
  ffcs:
    title: FFCS                 # used when rewriting follow-ups ("how does it work?" → "how does FFCS work?")
    summary: |                  # first answer (Markdown, rendered safely)
      **FFCS (Fully Flexible Credit System)** is ...
    details: |                  # returned for follow-up questions
      How FFCS works in practice: ...
    sources:                    # official pages the facts came from (shown as links)
      - https://vit.ac.in/academics/ffcs
    time_sensitive: false       # true adds "please verify the latest details" to the answer
    last_verified: "2026-09-24"
```

The file also contains:

- `responses`: short replies for conversational intents (greeting, goodbye, thanks, profanity, out_of_scope) and the fallbacks (`low_confidence`, `clarify_follow_up`, `unavailable`).
- `starter_questions`: suggested prompts for a new chat. At startup, the backend keeps only the prompts **that the trained model actually classifies as the listed intent**, so the UI never suggests a question the model gets wrong.

## Updating the knowledge base

1. Edit `data/knowledge/vit_knowledge.yaml`: update the text, sources and `last_verified`.
2. Run `pytest tests/test_knowledge_base.py`. It checks that every intent has an answer, that every VIT fact cites an `https://` official VIT source and has a verification date, and that starter questions refer to real intents.
3. Restart the backend. **No retraining is needed.**

Retraining is only needed when a **new intent** is added: add its utterances to `data/authored/`, rebuild the dataset and retrain.

## Static data, not a live mirror

The knowledge base is a snapshot of official VIT information collected during development. It is **not** synchronised with the website. Every time-sensitive answer (admissions, fees, rankings, contacts, placements and so on) therefore ends with a note asking the user to check the latest details on the official VIT website.
