# 02 · System Architecture

VITmate has three parts:

1. a **browser client** (React) that handles typing, speech recognition and locally persisted chat history
2. a **stateless Python API** (FastAPI) that runs the deep-learning intent classifier and the response engine
3. a **curated knowledge base** (YAML) of official VIT and other authoritative information

The design keeps two jobs apart. The neural network decides *what* the user is asking about, and the knowledge base decides *what VITmate answers*. Facts can therefore be corrected without retraining, and the model never has to memorise facts.

## 1. Overall system

```mermaid
%% file: system-architecture
flowchart TD
    User(["👤 Student"])

    subgraph Browser["Browser — React + TypeScript (Vite build)"]
        UI["Chat UI<br/>Sidebar · Header · ChatView · Composer"]
        Speak["Speak mode<br/>useSpeechRecognition"]
        Type["Type mode<br/>TextInput"]
        Send["handleSend()<br/>single pipeline for both modes"]
        Store[("IndexedDB<br/>conversations")]
        Prefs[("localStorage<br/>theme · input mode · banner")]
    end

    SR["Web Speech API<br/>(browser speech service)"]

    subgraph Server["FastAPI backend (stateless)"]
        API["/api/chat · /api/health · /api/suggestions<br/>validation · error mapping · CORS"]
        Engine["ChatEngine<br/>threshold · context · suggestions"]
        Model["IntentClassifier<br/>fine-tuned DistilBERT (67M)<br/>loaded once at startup"]
        KB[("vit_knowledge.yaml<br/>38 intents · sources · as_of")]
    end

    User -->|types| Type
    User -->|speaks| Speak
    Speak <-->|audio → text| SR
    Type --> Send
    Speak -->|final transcript| Send
    Send -->|"POST /api/chat {message, context, input_mode}"| API
    API --> Engine
    Engine -->|text| Model
    Model -->|intent + confidence + top-3| Engine
    KB --> Engine
    Engine -->|"reply · intent · confidence · sources · suggestions · context"| API
    API --> UI
    UI <--> Store
    UI <--> Prefs
```

## 2. Frontend and backend modules

```mermaid
%% file: frontend-backend-architecture
flowchart LR
    subgraph FE["frontend/src"]
        direction TB
        App["App.tsx<br/>orchestrates send · retry · thinking state"]
        subgraph Components["components/"]
            direction TB
            C1["Sidebar · Header · AboutModal · Modal"]
            C2["ChatView · MessageBubble<br/>(classifier readout · sources · did-you-mean)"]
            C3["Composer · ModeToggle · TextInput · VoiceInput"]
            C4["SpeechSupportBanner · SpeechSupportModal"]
        end
        subgraph Hooks["hooks/"]
            H1["useConversations<br/>(IndexedDB persistence, cross-tab sync)"]
            H2["useSpeechRecognition<br/>(continuous + silence window)"]
            H3["useTheme"]
        end
        subgraph Services["services/"]
            S1["api.ts (fetch, timeout, errors)"]
            S2["chatStore.ts (IndexedDB / localStorage)"]
            S3["speechSupport.ts (feature detection)"]
            S4["storage.ts (safe localStorage)"]
        end
        App --> Components
        App --> Hooks
        Hooks --> Services
    end

    subgraph BE["backend/app"]
        direction TB
        Main["main.py<br/>app factory · lifespan model load · static frontend"]
        Routes["api/routes.py + schemas.py"]
        Eng["chatbot/engine.py"]
        Ctx["chatbot/context.py"]
        Clf["ml/intent_classifier.py"]
        KBL["knowledge/knowledge_base.py"]
        Cfg["config.py (VITMATE_* env)"]
        Main --> Routes --> Eng
        Eng --> Ctx
        Eng --> Clf
        Eng --> KBL
        Main --> Cfg
    end

    S1 -->|HTTP JSON| Routes
```

## 3. Text interaction

```mermaid
%% file: text-interaction-sequence
sequenceDiagram
    autonumber
    actor U as Student
    participant UI as React UI
    participant DB as IndexedDB
    participant API as FastAPI /api/chat
    participant E as ChatEngine
    participant M as Intent model
    participant K as Knowledge base

    U->>UI: types "What is FFCS?" + Enter
    UI->>UI: show user message, "VITmate is thinking…"
    par request
        UI->>API: POST {message, context, input_mode: "text"}
        API->>API: validate (1–500 chars, strip control chars)
        API->>E: respond(message, context)
        E->>M: predict(text)
        M-->>E: ffcs (0.9x) + alternatives
        E->>K: entry("ffcs")
        K-->>E: summary, details, sources, as_of
        E-->>API: ChatResult
        API-->>UI: reply, intent, confidence, sources, suggestions, context
    and minimum thinking time
        UI->>UI: wait ≥ 450 ms (avoids a flash)
    end
    UI->>UI: render Markdown safely + classifier readout
    UI->>DB: put(conversation)
```

## 4. Response-engine decisions

Every message, typed or spoken, goes through the same decision flow in `ChatEngine.respond()`:

```mermaid
%% file: response-engine-flow
flowchart TD
    A["message + context<br/>{previous_intent, depth}"] --> B{"Current topic and<br/>'tell me more'?"}
    B -- yes --> D1["Topic details<br/>(depth 0 → 1)"]
    B -- no --> C["Classify message"]
    C --> P{"Topic and short pronoun<br/>follow-up ('how does it work?')"}
    P -- yes --> R["Rewrite: 'how does FFCS work?'<br/>and classify again"]
    R --> R1{"Same topic and<br/>confidence ≥ 0.35?"}
    R1 -- yes --> D1
    R1 -- no --> R2{"Original names another<br/>topic confidently?"}
    R2 -- no --> CL["Ask which topic<br/>+ suggestion chips"]
    R2 -- yes --> T
    P -- no --> T{"confidence ≥ 0.35?"}
    T -- no --> LC["'Did you mean…?'<br/>top VIT intents as chips<br/>(or ask to rephrase)"]
    T -- yes --> K{"Knowledge entry?"}
    K -- "no (greeting, thanks,<br/>out_of_scope, …)" --> CONV["Conversational reply<br/>topic kept"]
    K -- yes --> S{"Same as current topic?"}
    S -- yes --> D1
    S -- no --> ANS["Summary + sources<br/>+ dated note if time-sensitive"]
```

The server keeps **no session state**. Each reply returns `context = {previous_intent, depth}`, the browser stores it with the conversation, and it's sent back with the next message. The API therefore scales horizontally and survives restarts.

## 5. Knowledge and data flow

```mermaid
%% file: knowledge-data-flow
flowchart LR
    subgraph Sources["Authoritative sources (read 2026-09-24)"]
        V["vit.ac.in · viteee · vtop<br/>(primary)"]
        N["NIRF / Ministry of Education"]
        Q["QS · Times Higher Education"]
    end
    V --> R1["data/raw/vit_research_notes.json"]
    N --> R2["data/raw/external_sources_notes.json<br/>(values · years · URLs · discrepancies)"]
    Q --> R2
    R1 --> KB["data/knowledge/vit_knowledge.yaml<br/>curated by hand"]
    R2 --> KB
    KB --> T["tests/test_knowledge_base.py<br/>sources allowed? as_of present?<br/>every intent answerable?"]
    KB --> L["KnowledgeBase loader<br/>(startup)"]
    L --> E["ChatEngine"]
    E --> Resp["Answer + source links<br/>+ '🕒 Time-sensitive (as_of)' when needed"]
```

## 6. Chat-history persistence

```mermaid
%% file: chat-persistence
flowchart TD
    S["React state<br/>conversations[]"] -->|"each change"| D{"diff against<br/>what is stored"}
    D -->|changed / new| P["IndexedDB put(conversation)"]
    D -->|removed| X["IndexedDB delete(id)"]
    P --> BC["BroadcastChannel<br/>'vitmate-conversations'"]
    X --> BC
    BC -->|other open tabs| M["reload + mergeWithStored()<br/>newest copy wins"]
    M --> S
    L0["First run after upgrade"] -->|"migrate VITmate v1 data"| LS[("localStorage<br/>conversations.v1")]
    LS --> P
    NoIDB["No IndexedDB available"] -.->|fallback| LS
```

- **Storage:** one record per conversation in the `vitmate` IndexedDB database (object store `conversations`). The record holds every message with its intent, confidence, sources, suggestions and input mode, plus the conversation context.
- **Survives:** refreshes, browser restarts and reopening the site. `navigator.storage.persist()` is requested so the browser is less likely to evict the data.
- **Never** sent to a server. Private windows and clearing site data remove it.
- **Two tabs** never overwrite each other. Only changed conversations are written, and other tabs merge by `updatedAt`.

## Components

| Layer | Location | Responsibility |
|---|---|---|
| Speech recognition | `frontend/src/hooks/useSpeechRecognition.ts`, `services/speechSupport.ts` | Feature detection; continuous recognition with a silence window; mapping each error code to a message |
| Chat UI | `frontend/src/components/*` | Sidebar history, Type/Speak control, thread, thinking indicator, classifier readout, About, compatibility banner |
| Persistence | `frontend/src/services/chatStore.ts`, `hooks/useConversations.ts` | IndexedDB conversations; `localStorage` preferences |
| API | `backend/app/api/` | Endpoints, validation, error mapping |
| Intent model | `backend/app/ml/intent_classifier.py` | Loads the fine-tuned transformer once; returns intent, confidence and alternatives |
| Context | `backend/app/chatbot/context.py` | Detects follow-ups and rewrites pronouns with the current topic |
| Response engine | `backend/app/chatbot/engine.py` | Threshold, routing, suggestions, freshness notes |
| Knowledge base | `data/knowledge/vit_knowledge.yaml`, `backend/app/knowledge/` | Curated facts with sources and dates |

## Frontend design

- **Layout:** a ChatGPT-inspired chat layout that copies no brand. A collapsible history sidebar (a drawer below 900 px), a header with the theme toggle and About, the thread, and a composer with the animated **Type / Speak** segmented control.
- **Messages:** user bubbles on the right. Assistant replies have an avatar and safe Markdown (raw HTML is never rendered), source links, a **classifier readout** (intent, confidence with a meter and a High/Medium/Low label), and "did you mean" chips on unsure replies.
- **Thinking state:** "VITmate is thinking…" with animated dots is shown for at least 450 ms (never longer than the real request) in both Type and Speak modes.
- **Themes:** light and dark themes use CSS custom properties; the system preference is used on first visit and the choice is then remembered.
- **Accessibility:** semantic landmarks, ARIA labels, a live region for the thread, visible focus rings, keyboard-operable controls, focus-trapped dialogs and reduced-motion support.
- **About:** developer and registration number, GitHub repository link, and the AI-assisted-development acknowledgement.

## Backend design

- **Startup:** FastAPI app factory (`create_app`). The model and knowledge base are loaded **once** in the lifespan hook. If loading fails, `/api/health` reports `degraded` and `/api/chat` returns a friendly 503 instead of crashing.
- **Validation:** 1–500 characters, control characters stripped, `input_mode` restricted to `text` or `voice`, and unknown context intents ignored.
- **Errors:** JSON messages only, never stack traces or file paths. CORS is limited to configured origins, and API docs are disabled in production.
- **Configuration:** `VITMATE_*` environment variables or `.env`, with paths relative to the project root.

## Design decisions

| Decision | Reason | Alternatives rejected |
|---|---|---|
| Browser Web Speech API | No installation; no audio reaches VITmate's server; no server speech-to-text cost | Server-side Whisper: heavy CPU/RAM for a free-tier host, and uploads audio |
| Intent classification + knowledge base | Grounded answers that can be updated without retraining | Generative LLM: can hallucinate, needs an external API, doesn't meet the "trained deep-learning model" requirement |
| Fine-tuned transformer (DistilBERT) | Selected by the fair finalist comparison (validation macro-F1 tie within noise; better validation OOS recall); about 13 ms on CPU | bge-small: equally accurate within noise and faster, but lower validation OOS recall (it was the v1 choice); a generative LLM (see [04](04-model-development.md)) |
| Stateless API, context held by the client | Simple to scale and host; no session store | Server sessions or Redis: unnecessary infrastructure |
| IndexedDB for history | Large quota, per-record writes (safe with several tabs), durable | Single localStorage array (v1): whole-history overwrites and about 5 MB limit |
| No streaming | Answers are retrieved, not generated, and complete in milliseconds, so streaming would be cosmetic | Token streaming: nothing to stream |
