# VITmate: project instructions for Claude

VITmate is a voice-enabled, deep-learning campus assistant for VIT: a React/Vite frontend, a FastAPI backend, a fine-tuned transformer intent classifier and a curated YAML knowledge base. Detailed documentation lives in `docs/` (start with `docs/README.md`).

## Permanent style rule: no U+00B7 MIDDLE DOT

Never use Unicode U+00B7 MIDDLE DOT (the small centred dot sometimes used as a separator, as in "Python <middle dot> FastAPI") anywhere in VITmate. This covers:

- source code, comments and string literals
- UI text: labels, buttons, headings, subtitles, tooltips, the About section
- chatbot response templates and the knowledge base (`data/knowledge/vit_knowledge.yaml`)
- README.md and everything in `docs/`, including Markdown tables
- Mermaid diagrams, graph labels and captions, generated documentation
- all future modifications

Use commas, pipes (`|`), hyphens, colons, slashes, parentheses or Markdown lists instead:

- Good: `Python, FastAPI, React`
- Good: `accuracy 0.850 | macro-F1 0.850`
- Inside Markdown table cells and Mermaid labels, use commas: a `|` would break the table or edge-label syntax.

This rule is about U+00B7 only. The normal bullet character U+2022 is a different character.

The only allowed occurrences are inside third-party model files that must not be edited: the DistilBERT tokenizer vocabulary (`backend/trained_model/vocab.txt` and `tokenizer.json`) contains the character as a pretrained token.

Check before finishing any change (this should print nothing):

```bash
grep -rnI $'\xc2\xb7' . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git \
  --exclude-dir=artifacts --exclude-dir=.pytest_cache --exclude-dir=__pycache__ --exclude-dir=dist \
  --exclude-dir=trained_model
```

## Deployment

- Live app: https://vit-mate.vercel.app (Vercel project `vit-mate`, team `vit-mate`, Hobby plan). Details: `docs/10-deployment.md`.
- The Vercel project is connected to GitHub: **every push to `main` deploys to production.** Treat a push as a release.
- Deployment config lives in `pyproject.toml` (`[tool.vercel]`, runtime dependencies), `vercel.json` and `.python-version`. Keep `pyproject.toml` dependency pins identical to `backend/requirements.txt`.
- The ~1 GB function bundle needs `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` (already set for Production and Preview).
- The Vercel CLI needs Node.js 20 or newer (`PATH=/usr/bin:$PATH`); the default `node` on this machine is v16.

## Useful commands

```bash
pytest                                   # backend, knowledge base, dataset and model tests
cd frontend && npm test                  # frontend tests (Vitest)
cd frontend && npm run build             # type-check and production build (Node 18+)
python -m training.make_graphs           # regenerate docs/graphs from docs/results
python scripts/render_diagrams.py        # re-render docs/pictures from the Mermaid in docs/*.md
```
