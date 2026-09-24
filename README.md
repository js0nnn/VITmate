<div align="center">

<img src="frontend/public/favicon.svg" width="72" alt="VITmate logo" />

# VITmate

**Your VIT Campus Companion**

*VITmate: A Voice-Enabled Deep Learning-Based Campus Assistant for VIT*

</div>

---

VITmate is a chatbot for **VIT (Vellore Institute of Technology)** students. You can **type or speak** questions like "What is FFCS?", "What are the hostel facilities?" or "How is VIT ranked?". VITmate understands them with a **fine-tuned deep-learning model** and answers from a curated knowledge base of **official VIT and other authoritative sources**, with links.

> Hi! I'm **VITmate** 👋 — Your VIT Campus Companion. How can I help you today?

<p align="center">
  <img src="docs/pictures/screenshots/06_voice_answer.png" width="780" alt="VITmate answering a spoken question" />
</p>

## Why VITmate?

Answers about FFCS rules, attendance, exams, hostels, scholarships, placements or rankings are scattered across many pages and PDFs. VITmate puts them one question away, and it's honest about what it doesn't know: it never invents fees, dates or statistics.

## Features

- 🎙️ **Speak or type.** Browser speech recognition tolerates natural pauses, and both input methods feed one conversation.
- 🧠 **Real deep learning.** A fine-tuned transformer (DistilBERT, 67M parameters) classifies each question into one of 38 intents in about 13 ms on a CPU. The model was chosen by a measured, multi-seed comparison of five approaches.
- 🔍 **Transparent.** Every answer shows the model's **intent and confidence** and its **sources**.
- 🤔 **Helpful when unsure.** Instead of guessing, VITmate offers "did you mean…?" topics.
- 📚 **Grounded answers.** Time-sensitive facts (rankings, admissions, placements) carry their date.
- 💬 **Follow-ups work.** "What is FFCS?" → "How does it work?"
- 🗂️ **Persistent chat history** on your device (IndexedDB): grouped by date, reopen or delete chats, never uploaded.
- 🌗 Light and dark themes, a responsive layout, keyboard navigation, and an About section with project details.

## Quick start

**Requirements:** Python 3.10+, Node.js 18+. No GPU needed.

```bash
git clone https://github.com/js0nnn/VITmate.git
cd VITmate

# 1) Backend: API and model
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --port 8000

# 2) Frontend (in a second terminal)
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173**. The trained model is included, so no training is needed to run the app.

### 🎤 Voice input

Voice uses the speech recognition **built into your browser**. Use a recent **Google Chrome** or **Microsoft Edge** and allow microphone access. Firefox doesn't provide it, and Brave has the API but no speech service behind it; VITmate detects both and shows a notice. Type mode always works. Pages must be served over `https://` or `localhost`.

## Results at a glance

| Metric | Result |
|---|---|
| Test set (339 questions, 38 intents) | accuracy **0.850**, macro-F1 **0.850** |
| Spoken-style questions (120, held out) | accuracy **0.950**, macro-F1 **0.953** |
| Out-of-scope questions correctly declined | **90.6%** of 977 unseen |
| Speed | ~13 ms per question on a laptop CPU |

<p align="center"><img src="docs/graphs/final_comparison.png" width="780" alt="Model comparison graph" /></p>

Details: [Evaluation](docs/07-evaluation.md) | [Model comparison](docs/05-model-comparison.md) | [Results summary](docs/12-results-summary.md)

## Tech stack

| Part | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| Speech | Browser Web Speech API |
| Backend | Python, FastAPI |
| Model | PyTorch, Hugging Face Transformers (fine-tuned DistilBERT, CPU) |
| Knowledge | Curated YAML with sources (official VIT, NIRF, THE, NAAC) |
| Tests | pytest, Vitest, Testing Library |

## Documentation

The full technical write-up (architecture diagrams, dataset, model development and comparison, training, evaluation, speech recognition, knowledge base, deployment and limitations) is in **[docs/](docs/README.md)**.

## Tests

```bash
pytest                    # backend, knowledge base, dataset and model
cd frontend && npm test   # UI, speech, persistence
```

## Project

- **Developer:** B. Jaison Edward | Reg. No. 23BAI0094
- **Repository:** https://github.com/js0nnn/VITmate.git
- **Live demo:** not deployed yet. The project is set up for a free Vercel Hobby deployment (see [docs/10-deployment.md](docs/10-deployment.md)).

VITmate is a student lab project and **not an official VIT service**. Always confirm important details on [vit.ac.in](https://vit.ac.in/).

**AI-assisted development:** ChatGPT and Claude were used as professional AI-assisted development tools for architecture planning, implementation support, debugging, documentation, testing and technical review. Project direction, design decisions and final review were carried out by the developer. The chatbot itself calls no external AI service.

**Data credits:** University Chatbot Dataset by Tushar Paul (Apache 2.0); CLINC150 by Larson et al. (CC BY 3.0).
