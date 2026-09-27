# Dual-API Writer

A single-page, browser-based writing tool for long-form fiction (novel chapters of 8,000+ words) driven by two OpenAI-compatible chat APIs — by default GLM (z.ai) and NanoGPT (DeepSeek). Everything runs locally: stories, lore and settings stay in your browser.

The UI is in Portuguese (pt-PT).

## Files

| File | What it is |
|---|---|
| `dual-api-writer.html` | The whole app (HTML + CSS + JS, no build step, no dependencies). |
| `server.py` | Local server: serves the app and proxies API calls to get around browser CORS limits. Python 3.8+, standard library only. |
| `start.bat` | Windows launcher for `server.py` (uses the `py` launcher or `python`). |
| `index.html`, `params.json`, `stylesheets/`, `javascripts/`, `images/`, `fonts/` | Leftovers from the GitHub Pages generator; not part of the tool. |

## Running it

**Windows:** double-click `start.bat`. A console window opens (keep it open) and the browser opens at `http://localhost:8787/dual-api-writer.html`.

**Any OS:** `python3 server.py` (optionally `python3 server.py 8790` for another port), then open `http://localhost:8787/dual-api-writer.html`.

Then, in the sidebar:
1. Fill in URL, model and API key for Provider A and/or B.
2. Leave "Proxy local" as `http://localhost:8787/proxy` (clear it only if your provider allows direct browser calls).
3. For chapters: switch to **Modo Autor**, set **piso de palavras** (e.g. 5000) and keep **máx. continuações** at 4–6.

> **Your stories belong to the address you open the app from.** Browser storage is per origin: `http://localhost:8787/...`, `http://127.0.0.1:8787/...` and the file opened directly (`file://...`) each have separate data. Always use the same address. To move stories between them, use **Backup .json** in one and **Importar backup .json** in the other.

> **GitHub Pages:** because this branch is published by GitHub Pages, the app is also reachable at `https://<user>.github.io/test1/dual-api-writer.html`. That copy cannot use the local proxy (the proxy only accepts requests from localhost pages), so it only works with providers that allow direct browser calls. Prefer the local server.

## Features

**Writing loop**
- Chat mode and Author mode (brief → chapter, with chapter numbering).
- **Auto-continue**: when a reply is cut by `max_tokens`, or ends below the **word floor**, the app asks the model to continue the *same* chapter (it strips a trailing `<ledger>` scaffold block so the model doesn't start a new chapter). A live counter shows words vs. floor; if a chapter still ends short, the status bar says why.
- **Streaming** with live text; **Parar** keeps everything received so far. A stream that drops mid-way is kept and resumed.
- **Continuar geração** extends the last chapter; **regenerar** rewrites one (the original is kept if that fails).
- **Rever** (revise with instructions): give an instruction ("darken the confession, cut the flashback") for the whole chapter or only a passage you selected. The revision appears below the original with **aceitar / descartar / refazer revisão**; nothing changes until you accept.
- **Versões**: accepting a revision, regenerating or restoring keeps the previous text (up to 10 per chapter), and any of them can be restored.
- Retries with backoff on 429/5xx/network errors (honours `Retry-After`) and a per-request timeout.
- **Failover**: if the selected provider still fails after retries, the same request goes once to the other provider. Mixed chapters are labelled `A + B`.

**Context for long novels**
- Per-story **history limit** (words): older entries are replaced by an editable **"story so far" summary**, which the AI can update on demand or after each chapter.
- **Token meter** for the next request (system / lore / summary / history).
- Per-story **system prompt** and **lore selection**.

**Lorebook**
- Text files (`.md`, `.txt`): always sent, or keyword-triggered when the first line is `keys: name, alias`.
- **SillyTavern worldbook `.json`** import: keys, constant, disabled and order are respected.
- View/edit entries in the app.

**Data**
- Stored in IndexedDB (no 5MB localStorage limit); older localStorage data is migrated automatically.
- Multiple stories, `.txt` export, JSON backup and import.
- Option to keep API keys only for the current tab session.
- Per-provider **extra body JSON** (e.g. `{"frequency_penalty": 0.3}`; `null` removes a field such as `{"thinking": null}`).

## How it works (for developers)

- One `<script>` block in `dual-api-writer.html`. Main pieces:
  - `buildContext()` — assembles the request: system prompt + triggered lore + summary + trimmed history.
  - `callProvider()` / `readCompletion()` — one HTTP call with retries and timeout; reads SSE or plain JSON (decided by the first byte).
  - `generateWithAutoContinue()` — the round loop (cut-off / word-floor continuation, failover per round, progress callbacks for saving partial text).
  - `send()`, `manualContinue()`, `regenerate()`, `summarizeStory()` — user actions; all go through `beginGeneration()`/`endGeneration()` so only one generation runs at a time, and they write into the story they started in.
  - `Store` — IndexedDB key-value store (`chat:<id>`, `lorebooks`, `currentChatId`) with a localStorage fallback; `persistChats()` writes only changed stories, throttled.
- `server.py` forwards `POST /proxy` to the URL in the `X-Target-Url` header, streaming the response through; it only accepts requests whose Origin/Host is this local server (or a `file://` page) and only `http(s)` targets.

## What's left to do

Implemented from the audit: all listed bugs (B1–B21), the context manager (F1), lorebook (F2), streaming (F3), failover (part of F4), revision workflow with versions (F5), import (F6), sampling via extra body (F10), resilience (F12). Still open, roughly in order of value:

1. ~~Revision workflow (F5)~~ — done.
2. **First-class chapters (F7)** — titles, per-chapter brief and status, outline view, reorder, per-chapter word stats.
3. **Variants / swipes (F13)** — keep several generations per brief and switch between them.
4. **More dual-API modes (rest of F4)** — compare (same brief to both, side by side), outline → prose pipeline, alternating providers between continuation rounds.
5. **Prose tooling (F9)** — banned-phrase list with highlighter, repetition detector, POV/tense reminders.
6. **Continuity tracker (F8)** — character sheets injected when a character is mentioned, timeline.
7. **Exports (F11)** — Markdown with headings, EPUB, DOCX.
8. **Smaller items** — lore token budget cap; option to fail over immediately instead of retrying first; word floor only in Author mode; search & replace; model list from `/models`; request/cost log (F14–F17).

Known limitations:
- The summary tracks *how many* chapters it covers, not *which*: after deleting or regenerating an earlier chapter, use **refazer do zero**.
- Token counts are estimates (words × 1.6).
- Browser tests were run during development but are not in the repo yet.
