# 10 - Running and Deployment

## Running locally

**Requirements:** Python 3.10+ (tested on 3.12), Node.js 18+ (tested on 20), about 2 GB of disk for the Python packages. No GPU is needed.

### Backend (API + model)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # CPU-only PyTorch
uvicorn backend.app.main:app --reload --port 8000
```

`curl http://localhost:8000/api/health` should report `"model_loaded": true`. Interactive API docs are at http://localhost:8000/docs (development only).

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to port 8000)
```

Use **Chrome or Edge** for voice input. On Ubuntu, check `node --version`: if it's older than 18, install a newer Node.js (for example with `nvm`) before running `npm install`.

### Single-server mode (production-like)

```bash
cd frontend && npm run build && cd ..
VITMATE_ENV=production uvicorn backend.app.main:app --port 8000
```

When `frontend/dist/` exists, FastAPI serves the built app at `/`, so everything runs on one port.

## Reproducing the ML pipeline

| Step | Command | Output |
|---|---|---|
| Build dataset | `python -m training.build_dataset` | `data/processed/` |
| Compare models | `python -m training.compare_models` then `--only <top-2> --seeds 7 13` | `docs/results/model_comparison.{json,md}` |
| Train final model | `python -m training.train` | `backend/trained_model/` |
| Evaluate | `python -m training.evaluate` | `docs/results/evaluation.{json,md}`, confusion matrix, threshold sweep |
| Graphs | `python -m training.make_graphs` | `docs/graphs/*.png` |
| Diagrams | `PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome python scripts/render_diagrams.py` | `docs/pictures/*.svg, *.png` (needs mermaid-cli) |

Candidate checkpoints go to `artifacts/` (git-ignored, about 1 GB, reproducible).

## Configuration

Copy `.env.example` to `.env`. All settings are optional.

| Variable | Default | Purpose |
|---|---|---|
| `VITMATE_ENV` | `development` | `production` hides the API docs |
| `VITMATE_CONFIDENCE_THRESHOLD` | `0.35` | Below this, VITmate doesn't answer; it offers "did you mean" topics or asks the user to rephrase (value chosen on the validation set) |
| `VITMATE_CORS_ORIGINS` | localhost:5173 | Allowed browser origins (JSON list) |
| `VITMATE_MODEL_DIR`, `VITMATE_KNOWLEDGE_FILE`, `VITMATE_FRONTEND_DIST` | project paths | Relative to the project root |
| `VITMATE_MAX_MESSAGE_LENGTH` | `500` | Input limit |
| `VITMATE_TORCH_THREADS` | unset | Cap CPU threads on small hosts |
| `VITE_API_BASE_URL` (frontend) | empty | Set when the API is on another origin |

## Deployment readiness

Hosting is **not** configured yet, but the code is ready for it:

- **No machine-specific paths:** everything is project-relative or set through `VITMATE_*` variables.
- **Stateless API:** conversation context round-trips through the client, and chat history lives in the user's browser (IndexedDB), so no database is needed.
- **CPU only:** the fp16 checkpoint is 134 MB (two shards). A fresh process that loads the model and serves queries used about 0.68 GB RSS (see [07-evaluation.md](07-evaluation.md)).
- **One service** can serve both the API and the built frontend, which suits free tiers such as Hugging Face Spaces, Render or Railway.
- **Errors never expose stack traces or file paths**, and `VITMATE_ENV=production` disables `/docs`.

Remaining steps when hosting:

1. Choose a host with about 1 GB of RAM.
2. Add a Dockerfile or start command: `npm run build`, then `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
3. Set `VITMATE_ENV=production` and `VITMATE_CORS_ORIGINS`.
4. Serve over **HTTPS**, because browsers only allow microphone access on secure origins.
5. The weights are stored as two shards (85 MB + 48 MB), each under GitHub's 100 MB per-file limit, so Git LFS isn't required.
