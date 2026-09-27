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

**Chapters (Author mode)**
- Each chapter has a **title** (click the "Capítulo N" divider) and a **status**: rascunho / revisto / final. Titles are included in the `.txt` export.
- **Planear** saves a brief as a planned chapter without generating it; generate any planned chapter later with **gerar este capítulo**, in place, without touching the chapters after it. Unwritten briefs are never sent as context.
- **☷ Capítulos** opens the outline: every chapter with title, status, brief and a word-count bar (chapters well below the average are flagged), plus jump, move up/down, rename, merge with the next one, and generate for planned chapters.
- **dividir** splits a chapter in two at the cursor (click in the text first).

**Outline → prose (Author mode)**
- **modo de escrita: plano → prosa**: before writing, a model produces a numbered **beat outline** (8–16 beats sized to the word floor); the chapter is then written following it. The outline can be written by the other provider (e.g. a fast/cheap model plans, the strong one writes).
- With **parar para rever o plano**, the outline appears under the brief as editable text; **escrever capítulo com este plano** writes the prose. **criar plano** / **refazer plano** / **remover plano** work on any brief, also in direct mode.
- The outline stays with its brief and is also used by regenerar, variantes and Continuar; it is never sent with other chapters.
- **alternar providers entre continuações**: continuation rounds alternate between the two APIs, to break repetition loops in very long chapters.

**Continuity (per story) — ☺ Continuidade**
- **Personagens**: a sheet per character (name, nicknames, appearance, scars/marks, relationships, current state/arc, notes). A sheet is sent only when the name or a nickname appears in the brief, the end of the previous chapter or the summary — or always, with "sempre enviar".
- **Cronologia**: events in story order (free-text "when"), optionally sent with every request — useful for flashbacks.
- **continuidade** on a chapter: **verificar contradições** (the model checks the chapter against the sheets, timeline and summary; **rever para corrigir** pre-fills a revision) and **atualizar fichas com este capítulo** (the model proposes sheet changes, new characters and events; tick what to keep and **aplicar**).

**Prose quality (per story)**
- **Frases proibidas**: one phrase per line (or `/regex/`); matched whole-word, ignoring case and spacing. Sent to the model as banned (optional) and **highlighted** in the chapters, with a ⚠ count next to each chapter. **inserir lista sugerida** adds a starter list of common PT/EN clichés.
- **Ponto de vista / tempo verbal**: a narrative lock (e.g. 3rd person limited, past) added to every request.
- **análise** per chapter: banned phrases, the most repeated 3–5-word expressions, em-dash and ellipsis rates (flagged when high); **rever para corrigir** opens "rever" with an instruction listing exactly those problems.
- **analisar a história toda**: problems per chapter and verbal tics that recur across several chapters.

**Variants**
- **nova variante** writes another version of a chapter from the same brief and context; **variante com <other provider>** does it with the other API, to compare them. Flip with **‹ 2/3 ›** next to the word count.
- The shown variant *is* the chapter (context, export, summary). Edits, revisions and "Continuar" apply to the shown variant and are kept when you flip.
- **apagar variante** removes the shown one (its text stays in "versões"). Up to 20 variants per chapter; splitting or merging a chapter keeps only the shown variant.
- Retries with backoff on 429/5xx/network errors (honours `Retry-After`) and a per-request timeout.
- **Failover**: if the selected provider still fails after retries, the same request goes once to the other provider. Mixed chapters are labelled `A + B`. With **failover imediato** it switches on the first error, without retrying.
- The **word floor** applies in Author mode only (a checkbox extends it to Chat mode).

**Context for long novels**
- Per-story **history limit** (words): older entries are replaced by an editable **"story so far" summary**, which the AI can update on demand or after each chapter.
- **Token meter** for the next request (system / lore / summary / history).
- Per-story **system prompt** and **lore selection**.

**Lorebook**
- Text files (`.md`, `.txt`): always sent, or keyword-triggered when the first line is `keys: name, alias`.
- **SillyTavern worldbook `.json`** import: keys, constant, disabled and order are respected.
- View/edit entries in the app.
- **Lore limit per request** (words): always-sent entries first, then keyword hits; what does not fit is listed in the token meter.

**Data**
- Stored in IndexedDB (no 5MB localStorage limit); older localStorage data is migrated automatically.
- Multiple stories, JSON backup and import.
- **Exportar…**: `.txt`, `.md`, **`.epub`** (title page, table of contents, one file per chapter; passes EPUBCheck with no errors or warnings) and **`.docx`** (title page, each chapter on a new page, book-style paragraphs). Book title (per story) and author are set in the export panel; `*italic*`/`**bold**` become real formatting and `* * *` lines become scene breaks. "Remover blocos de estrutura" (on by default) strips `<plan>`, `<ledger>`, `<self-check>` and `[DIRECTIONS]` from exports and "Copiar tudo". Everything is built in the browser (small built-in ZIP writer, no libraries).
- Option to keep API keys only for the current tab session.
- Per-provider **extra body JSON** (e.g. `{"frequency_penalty": 0.3}`; `null` removes a field such as `{"thinking": null}`).
- **↻** next to each model field loads the provider's model list (`/models`), directly or through the proxy.
- **🔍 Procurar**: search the whole story (case, whole-word, regex, include briefs), jump to results, and **substituir tudo** (changed chapters keep their previous text in "versões").
- **📊 Registo de pedidos e custos**: every request with provider, model, tokens (real when the provider reports them, otherwise estimated "~"), duration and result; totals per provider and per story, and cost from the per-provider prices (US$ per 1M tokens). CSV export.

## How it works (for developers)

- One `<script>` block in `dual-api-writer.html`. Main pieces:
  - `buildContext()` — assembles the request: system prompt + triggered lore + summary + trimmed history.
  - `callProvider()` / `readCompletion()` — one HTTP call with retries and timeout; reads SSE or plain JSON (decided by the first byte).
  - `generateWithAutoContinue()` — the round loop (cut-off / word-floor continuation, failover per round, progress callbacks for saving partial text).
  - `send()`, `manualContinue()`, `regenerate()`, `summarizeStory()` — user actions; all go through `beginGeneration()`/`endGeneration()` so only one generation runs at a time, and they write into the story they started in.
  - `Store` — IndexedDB key-value store (`chat:<id>`, `lorebooks`, `currentChatId`) with a localStorage fallback; `persistChats()` writes only changed stories, throttled.
- `server.py` forwards `POST /proxy` to the URL in the `X-Target-Url` header, streaming the response through; it only accepts requests whose Origin/Host is this local server (or a `file://` page) and only `http(s)` targets.

## What's left to do

Everything from the audit is implemented: all listed bugs (B1–B21) and features F1–F17, except where noted below.

1. ~~Revision workflow (F5)~~ — done.
2. ~~First-class chapters (F7)~~ — done.
3. ~~Variants / swipes (F13)~~ — done (including "variant with the other provider" for comparing).
4. ~~More dual-API modes (rest of F4)~~ — done: outline → prose pipeline, alternating providers between continuation rounds (compare mode is covered by variants).
5. ~~Prose tooling (F9)~~ — done.
6. ~~Continuity tracker (F8)~~ — done.
7. ~~Exports (F11)~~ — done.
8. ~~Smaller items~~ — done: lore budget, immediate failover, floor only in Author mode, search & replace, model list, request/cost log.

Not done (deliberately):
- **PWA / offline install (F15)** — the app already works offline from the local server; the data already lives in IndexedDB.
- **Distraction-free reading mode, prompt/preset library (F14, F16)** — small, can be added if wanted.

Known limitations:
- The summary tracks *how many* chapters it covers, not *which*: after deleting, regenerating, reordering, merging, splitting or generating an earlier chapter, use **refazer do zero** (the app reminds you).
- Token counts in the meter are estimates (words × 1.6); the request log uses the provider's real counts when it sends them.
- Browser tests were run during development but are not in the repo yet.
