# Setting up Gemini 3.1 Flash Lite for the Detective node

The **detective_node** (in `agents/nodes.py`) uses an LLM to analyze competitor data and return structured JSON (signals, confidence, problem patterns). You can run it with **Gemini 3.1 Flash Lite** for faster, cost-effective inference.

## 1. Get a Google AI API key

1. Open [Google AI Studio](https://aistudio.google.com/apikey).
2. Create or select a project and click **Create API key**.
3. Copy the key (starts with `AIza...`).

## 2. Configure environment

In your **`.env`** (in the project folder), set:

```bash
# Use Gemini as the LLM provider (for Detective and other nodes)
LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIza...your-key-here
```

To use **Gemini 3.1 Flash Lite** explicitly (this is now the default when `LLM_PROVIDER=gemini`):

```bash
GEMINI_MODEL=gemini-3.1-flash-lite-preview
```

If you omit `GEMINI_MODEL`, the code uses `gemini-3.1-flash-lite-preview` by default when `LLM_PROVIDER=gemini`.

## 3. How it’s used in the Detective node

- **`agents/llm_config.py`**  
  - `get_llm()` and `get_llm_json()` read `LLM_PROVIDER` and `GEMINI_MODEL`.  
  - For `LLM_PROVIDER=gemini`, they build a `ChatGoogleGenerativeAI` with `model=GEMINI_MODEL` (default `gemini-3.1-flash-lite-preview`).

- **`agents/nodes.py`**  
  - At import time: `_llm_json = get_llm_json()`.  
  - In **`detective_node(state)`**: the prompt is sent with `_llm_json.invoke(prompt)`; the response is parsed as JSON and used for signals and confidence.

So once `LLM_PROVIDER=gemini` and `GOOGLE_API_KEY` are set, the Detective node automatically uses Gemini 3.1 Flash Lite (or whatever you set in `GEMINI_MODEL`).

## 4. Optional: embeddings with Gemini

To use Gemini for embeddings as well (e.g. for review search used by the Detective):

```bash
EMBEDDING_PROVIDER=gemini
```

Same `GOOGLE_API_KEY` is used. The embedding model is configured in `api/vector_db.py` (e.g. `gemini-embedding-2-preview`).

## 5. Verify

1. Restart the backend after changing `.env`.
2. Run a scan from the dashboard.
3. Check logs for `[DETECTIVE]` lines; if you see “Signal extraction complete” and no Gemini/API errors, the Detective node is using Gemini 3.1 Flash Lite (or your chosen model) successfully.

## Model reference

| Env var        | Value                             | Use case                          |
|----------------|-----------------------------------|-----------------------------------|
| `GEMINI_MODEL` | `gemini-3.1-flash-lite-preview`   | Default: fast, cost-effective     |
| `GEMINI_MODEL` | `gemini-2.0-flash`                | Alternative Gemini 2.0            |
| `GEMINI_MODEL` | `gemini-2.5-flash`                | If you need a different variant   |

[Gemini 3.1 Flash Lite (Google AI for Developers)](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-preview)
