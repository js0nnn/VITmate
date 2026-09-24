# 09 · Knowledge Base

File: [`data/knowledge/vit_knowledge.yaml`](../data/knowledge/vit_knowledge.yaml) · Loader: `backend/app/knowledge/knowledge_base.py`

The intent classifier decides **what** the user is asking about. The knowledge base decides **what VITmate answers**. The neural network never memorises facts, so answers are corrected or updated by editing one YAML file, with **no retraining**.

## Sources and how they were used

| Tier | Sources | Used for |
|---|---|---|
| **Primary (official VIT)** | vit.ac.in, viteee.vit.ac.in, vtop.vit.ac.in, blogs.vit.ac.in, the FFCS Academic Regulations PDF, **VIT's NIRF data submissions** (vit.ac.in/files/nirf/) | Everything about programmes, rules, services, contacts; research, patent and placement figures |
| **Authoritative external** | **NIRF** (nirfindia.org, Ministry of Education) · **Times Higher Education** · **NAAC** (naac.gov.in) · **ABET** public database · **PIB** (Government press releases) | Rankings, accreditation and verification of VIT's claims |
| **Attempted, not accessible** | QS (topuniversities.com returned HTTP 403) | QS ranks are attributed to VIT's own announcements |
| **Never used** | Reddit, blogs, news/SEO "top colleges" sites, social media | — |

Research notes with every value, year, URL and confidence level:

- `data/raw/vit_research_notes.json`: official VIT pages, v1
- `data/raw/external_sources_notes.json`: NIRF, THE, NAAC, ABET, PIB and VIT's NIRF data, with 63 facts, 12 discrepancies and 8 inaccessible URLs (v2)

Everything was retrieved on **24 September 2026**.

## Discrepancies: recorded, not hidden

When sources disagree, VITmate doesn't silently pick one. It prefers the most authoritative current source and mentions the difference where it matters.

| Topic | Conflict | How VITmate answers |
|---|---|---|
| **ABET** | VIT's 2020 PDF says 14 B.Tech programmes are ABET-accredited; ABET's database shows all VIT records ended on **30 Sep 2021** | States ABET's current status; the v1 claim "B.Tech programmes hold ABET accreditation" was **removed** |
| **Institution of Eminence** | VIT pages and THE's profile text say IoE; the Government (PIB, Sep 2019) confirms only a **Letter of Intent** | States the Letter of Intent and that no final declaration was found; the v1 wording was **removed** |
| **QS rank** | VIT's ranking page calls 691 the 2027 rank; its milestones page says 2026; VIT's blog (18 Jun 2026) reports **597 for 2027** | Gives 597 (2027) and 691 (2026) as VIT's announcements, noting that QS couldn't be checked directly |
| **Patents published in 2024** | NIRF 2026 submission: **508**; VIT IPR Cell list (to Feb 2025): **152** | Gives the NIRF figures with years and mentions the IPR Cell count |
| **Placements** | CDC figures (all four campuses, internships included) vs NIRF (Vellore graduates) | Both are given with their scope and year, with an explicit "don't compare directly" |

## What is deliberately *not* stated

- **Fee amounts** (they change every year and depend on fee category; VITmate links to the official fee pages)
- **Library hours and fines** (shown only on the library's display boards)
- **Bus routes and timings** (not published)
- **Names of individual HODs and deans** (VITmate points to the faculty directory)
- **Travel directions and distances** (no official source)
- **Opinions** ("VIT is the best"). For "Is VIT good?", VITmate answers with documented facts (NIRF 2025 rank, NAAC A++, campuses, programmes) and then invites a more specific question.

## Entry format

```yaml
entries:
  rankings:
    title: VIT's rankings                  # used to rewrite follow-ups ("is it improving?")
    example_question: "How is VIT ranked?" # offered as a "did you mean" chip
    summary: |                             # first answer: friendly opener + structured facts
      Here's where VIT stands in the most recent rankings …
    details: |                             # returned for "tell me more"
      A little more context: …
    sources: [https://www.nirfindia.org/…, https://www.timeshighereducation.com/…]
    time_sensitive: true                   # add a one-time dated freshness note
    as_of: "NIRF 2025, THE 2026, QS 2026–2027; checked 24 September 2026"
    last_verified: "2026-09-24"
```

The file also holds:

- **`responses`:** conversational replies and fallbacks (`low_confidence`, `low_confidence_suggest`, `clarify_follow_up`, `unavailable`, …)
- **`starter_questions`:** prompts for a new chat. At startup, the backend keeps only those the trained model classifies as their listed intent.

## Response style (v2)

The v1 answers read like documentation and ended almost every reply with "This information can change — please check the latest details on the official VIT website."

v2 answers:

1. **Open conversationally.** "It depends on the programme. For B.Tech, the main route is VITEEE. Here's how the major programmes work:"
2. **Give the facts in a structured form.** Bullets with bold key values.
3. **Show sources** as links under the answer.
4. **Add a freshness note only when it's genuinely needed.** Only entries with `time_sensitive: true` get it: admissions, VITEEE, fees, scholarships, placements, academic calendar, programme list, rankings and research. The note appears **once**, with the first answer, and states the entry's date: "🕒 Time-sensitive information. As of: NIRF 2025, THE 2026, … Please confirm on the official source before relying on it." Stable topics such as FFCS, hostels and the library carry no note.

The persistent UI disclaimer stays below the input box: "VITmate answers from official VIT information and can make mistakes. Verify important details on vit.ac.in."

## Updating

1. Edit the YAML: text, `sources`, `as_of` and `last_verified`.
2. Run `pytest tests/test_knowledge_base.py`. It checks that:
   - every intent is answerable
   - every source is `https://` on an allowed host
   - every entry cites at least one official VIT page
   - time-sensitive entries have `as_of`
   - every VIT topic has an `example_question`
3. Restart the backend.

Retraining is only needed for a **new intent** (add utterances in `data/authored/`, rebuild the dataset and retrain), as was done for `rankings` and `research_patents` in v2.

## Snapshot, not a live mirror

The knowledge base is a snapshot collected during development and is **not** synchronised with the VIT website. The NIRF 2026 rankings, for example, weren't published when the data was collected. Update it periodically.
