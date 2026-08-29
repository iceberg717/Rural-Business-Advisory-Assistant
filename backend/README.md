# Mehsana GraphRAG Business Advisory System

A GraphRAG-based advisory assistant for rural micro-entrepreneurs in Mehsana
district, Gujarat — built for SIH 2026 (Problem Statement SIH26091).

## What's in this package

### 1. Raw → Cleaned data pipeline
- `clean_data.py` — parses all 6 original files (Agriculture CSV, Population
  XLSX, MSME XLSX, Financial CSV, Market Price JSON, Literacy JSON) into
  consistent CSVs, joining Agriculture↔Population villages by normalized name.
- `disambiguate_villages.py` — resolves ambiguous village-taluka matches using
  population similarity (92% match rate after this step).
- `add_taluka_to_msme.py` — extracts taluka from MSME address text (89% coverage).
- `flatten_real_schemes.py` — flattens the 7 real government schemes JSON.
- **Output:** `population_clean.csv`, `agriculture_clean.csv`, `msme_clean.csv`,
  `financial_clean.csv`, `market_prices_clean.csv`, `literacy_summary_clean.csv`,
  `real_schemes_clean.csv`

### 2. Chunking + Vector DB
- `make_chunks.py` — converts every row across all 7 datasets into a natural-
  language text chunk (65,212 chunks total).
- `embed_and_store.py` — embeds chunks with TF-IDF (no external model download
  needed — see note below) and stores them in a persistent Chroma vector DB
  (`mehsana_vectordb/`).
- `colab_real_embeddings.py` — **run this in Google Colab** (free) to upgrade
  from TF-IDF to real neural embeddings (`sentence-transformers`). Produces a
  drop-in replacement `mehsana_vectordb/` folder. Not runnable here — this
  sandbox has no internet access to HuggingFace.

### 3. Graph layer
- `build_graph.py` — builds a NetworkX graph: Village, Taluka, Crop, Enterprise,
  Activity, Scheme, Sector, Commodity, RealScheme, BusinessType nodes with real
  relationship edges (LOCATED_IN, GROWS, ENGAGES_IN, SUITED_FOR, IS_A, etc).
  65,862 nodes, 143,756 edges.
- `mehsana_graph.pkl` — the graph (Python pickle, load with `pickle.load`)
- `mehsana_graph.graphml` — same graph, open in Gephi/yEd/Neo4j for a visual demo
- `test_graph.py` — example multi-hop traversal queries

### 4. Retrieval
- `hybrid_retriever.py` — routes ranking queries ("top 3", "highest") to exact
  pandas computation; routes descriptive queries to vector search, auto-filtered
  by likely source dataset.
- `graphrag_retriever.py` — the full GraphRAG retriever: vector search finds a
  seed chunk → maps it to its graph node → traverses N hops outward to pull
  connected context (e.g. "wheat price" query automatically surfaces villages
  that grow wheat, via the graph, not just the price fact).

### 5. Business features
- `match_schemes.py` — matches a business type (e.g. "dairy") against the 7 real
  government schemes via graph traversal (`RealScheme --SUITED_FOR--> BusinessType`).
- `shortlist_competitors.py` — two-layer competitor shortlist:
  - **Keyword filter** (the real shortlist): exact category matches from
    `activity_descriptions`, scoped to a taluka. Precise and complete.
  - **Vector similarity** (secondary layer): TF-IDF search for adjacent/related
    businesses. Honest caveat: this layer is weak with TF-IDF — upgrade to real
    embeddings (see `colab_real_embeddings.py`) for it to be genuinely useful.
- `advisory_assistant.py` — the orchestrator. `advise(user_text, taluka)`:
  1. Extracts business type from free text (keyword match against
     `CATEGORY_KEYWORDS` — currently covers dairy, retail, food processing,
     textile, computer/IT, repair, agri-business — extend this list for more)
  2. Asks for a taluka if none given
  3. Runs `match_schemes()` + `shortlist_competitors()` + graph-based crop context
  4. Generates a report — either a deterministic template (no API needed, works
     now) or hands the same real data to an LLM for a natural write-up
- `gemini_integration.py` — example LLM wrapper using Google Gemini. **Run
  outside this sandbox** (Colab/your machine) with your own API key set as an
  environment variable (`GEMINI_API_KEY`) — never hardcode it.
  Swap in any other LLM (OpenAI, Claude, local model) by writing a function of
  the same shape: `def my_llm_call(prompt: str) -> str: ...`, then pass it as
  `api_call_fn` to `advise()`.

## Quick start

```bash
pip install chromadb scikit-learn networkx pandas

# regenerate everything from scratch (optional — cleaned files already included)
python3 clean_data.py
python3 disambiguate_villages.py
python3 add_taluka_to_msme.py
python3 flatten_real_schemes.py
python3 make_chunks.py
python3 embed_and_store.py
python3 build_graph.py

# use the advisory assistant (template mode, no API key needed)
python3 advisory_assistant.py

# with a real LLM (after setting GEMINI_API_KEY, outside this sandbox)
python3 gemini_integration.py
```

## Known limitations (honest, not hidden)
- **~8% of agriculture villages** (48 of 603) couldn't be matched to a taluka
  confidently — flagged as `AMBIGUOUS`/`UNMATCHED` in `agriculture_clean.csv`,
  excluded from graph edges rather than guessed.
- **TF-IDF embeddings**, not true neural embeddings — good for keyword-heavy
  domain terms (village/crop/scheme names), weak for paraphrase/semantic
  matching. Upgrade path: `colab_real_embeddings.py`.
- **MSME taluka is extracted from address text**, not authoritative geocoding
  (89% coverage) — good enough for a demo, not survey-grade.
- **`advisory_assistant.py`'s business-type extraction** only covers 7 hardcoded
  categories — extend `CATEGORY_KEYWORDS` in `shortlist_competitors.py` for more.
- **No true GPS radius search** for "nearby businesses" — MSME data only has
  pincode + address text, not coordinates. Current proxy is same-taluka
  matching. For real radius search, you'd need a pincode→lat/long lookup table.
