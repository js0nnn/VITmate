# 01 - Project Overview

**Title:** VITmate: A Voice-Enabled Deep Learning-Based Campus Assistant for VIT
**Product name:** VITmate — Your VIT Campus Companion
**Developer:** B. Jaison Edward (Reg. No. 23BAI0094)
**Repository:** https://github.com/js0nnn/VITmate.git
**Live app:** https://vit-mate.vercel.app

## Introduction

Students at VIT often need quick answers about:

- academic rules (FFCS, attendance, CAT/FAT)
- campus services (hostels, mess, library, health centre)
- admissions (VITEEE, scholarships)
- careers (placements, internships)
- the university's standing (rankings, research)

This information is spread across many pages of the official website and PDF regulations. **VITmate** accepts **spoken or typed** questions, identifies the intent with a **deep-learning classifier**, and answers from a curated knowledge base of **official VIT and other authoritative information**, with source links.

## Problem statement

Develop and deploy an online voice-enabled chatbot that:

- converts speech to text with a suitable speech-recognition technique
- understands the text with a deep-learning intent-classification model
- returns an appropriate response
- displays both the recognised speech and the response

For a university assistant, the answers must also be **factually grounded**. The system must not invent fees, dates, statistics or policies, and it must recognise questions that are out of scope.

## Objectives

1. Build a VIT-specific intent dataset by adapting an existing university chatbot dataset.
2. Train and compare deep-learning intent classifiers, and select one by measured validation performance.
3. Separate intent recognition (the neural network) from factual answers (the knowledge base).
4. Integrate browser-based speech recognition that needs no installation and tolerates natural pauses.
5. Handle out-of-scope, ambiguous and low-confidence inputs safely and helpfully.
6. Provide a polished, responsive, accessible chat interface with persistent local history and themes.
7. Evaluate with standard metrics (accuracy, precision, recall, macro/weighted F1, confusion matrix, OOS recall, latency and memory) and document the whole development honestly.

## What the final system does

| Capability | How |
|---|---|
| Voice and text input, one pipeline | Web Speech API (continuous, with a silence window) → `handleSend()` ← textarea |
| Intent classification | Fine-tuned **DistilBERT** transformer (67M parameters), 38 intents, CPU (v1: bge-small) |
| Grounded answers | YAML knowledge base with sources, `as_of` dates and follow-up details |
| Ambiguity handling | Confidence threshold 0.35; "did you mean" suggestions from the model's top VIT intents; clarification for unresolved follow-ups |
| Out-of-scope handling | a dedicated `out_of_scope` class plus the threshold |
| Conversation context | stateless round-trip `{previous_intent, depth}`; pronoun rewriting |
| History | IndexedDB, grouped Today / Yesterday / Previous 7 Days / Older; restore and delete |
| Transparency | each answer shows the predicted **intent and confidence** and its **sources** |
| Compatibility | the banner and "Learn more" dialog appear only where speech recognition is unavailable |

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite 5, react-markdown (raw HTML disabled), lucide-react icons |
| Speech | Browser Web Speech API |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic settings |
| ML | PyTorch (CPU), Hugging Face Transformers, scikit-learn (baseline and metrics), matplotlib |
| Data | YAML / JSON / JSONL files; no database |
| Tests | pytest, Vitest + Testing Library, fake-indexeddb |
| Hosting | Vercel Hobby (free): one Python function serving the API, model and frontend ([10](10-deployment.md)) |

## Development phases (actual history)

1. **Research:**
   - inspected the Kaggle University Chatbot Dataset (39 intents, 412 patterns, many placeholder responses)
   - collected official VIT information
2. **Dataset v1:** 36 intents and 2,119 examples from Kaggle, authored and CLINC150 data ([03-dataset.md](03-dataset.md)).
3. **Model comparison v1:** baseline and four transformers. After probing, a robustness batch was added and **all** candidates were retrained. bge-small was selected by mean validation macro-F1 over 3 seeds ([04-model-development.md](04-model-development.md)).
4. **Application:** FastAPI backend, React frontend, speech, history, themes, About.
5. **Version 2 (this iteration):**
   - pause-tolerant speech and the compatibility banner
   - IndexedDB history
   - "did you mean" suggestions, conversational answers and dated freshness notes
   - new intents `rankings` and `research_patents` with NIRF/QS/THE sources
   - weak-intent examples
   - dataset v2, re-comparison and a fair finalist comparison at the deployed threshold, which selected DistilBERT
   - reorganised documentation, graphs and diagrams
6. **Deployment:** published on Vercel Hobby at https://vit-mate.vercel.app. The first build failed at the 500 MB function limit; enabling Large Functions fixed it, and pushes to `main` now deploy automatically ([10](10-deployment.md)).

## Acknowledgement

ChatGPT and Claude were used as professional AI-assisted development tools for architecture planning, implementation support, debugging, documentation, testing and technical review. Project direction, design decisions and final review were carried out by the developer. The deployed chatbot doesn't call any external AI service; its answers come from the trained classifier and the knowledge base.
