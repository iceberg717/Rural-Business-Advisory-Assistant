"""
Hybrid retriever for the Mehsana RAG system.

Two retrieval paths, chosen automatically per query:
  1. RANKING queries ("highest", "lowest", "top N", "most", "least", "biggest")
     -> answered by direct pandas computation on the cleaned CSVs (exact, not similarity search)
  2. Everything else -> vector search, auto-filtered to the most
     relevant source dataset so small tables (schemes, market_price) don't get
     drowned out by large ones (msme: 63,925 rows).
"""
import re
import pickle
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

# ---------- load vector DB + embedder ----------
client = chromadb.PersistentClient(path="./mehsana_vectordb")
collection = client.get_or_create_collection(name="mehsana_rag", metadata={"hnsw:space": "cosine"})
model = SentenceTransformer("all-MiniLM-L6-v2")

# ---------- load cleaned CSVs for the ranking path ----------
population_df = pd.read_csv("population_clean.csv")
agriculture_df = pd.read_csv("agriculture_clean.csv")
financial_df = pd.read_csv("financial_clean.csv")
prices_df = pd.read_csv("market_prices_clean.csv")

RANKABLE_FIELDS = {
    "population":        (population_df, "total_p", "population"),
    "literacy":          (population_df, "p_lit", "literate population"),
    "female literacy":   (population_df, "f_lit", "female literate population"),
    "male literacy":     (population_df, "m_lit", "male literate population"),
    "households":        (population_df, "no_hh", "households"),
    "sc population":     (population_df, "p_sc", "SC population"),
    "st population":     (population_df, "p_st", "ST population"),
    "cultivators":       (population_df, "main_cl_p", "cultivators"),
    "agri labourers":    (population_df, "main_al_p", "agricultural labourers"),
    "irrigated area":    (agriculture_df, "tot_irrigated", "irrigated area (ha)"),
    "income":            (agriculture_df, "tot_income", "annual income (₹)"),
    "loan amount":       (financial_df, "indicative_loan_amount_inr", "loan amount (₹)"),
    "emi":               (financial_df, "estimated_monthly_emi_inr", "EMI (₹)"),
    "price":             (prices_df, "price_rs_per_quintal", "market price (₹/quintal)"),
    "msp":               (prices_df, "msp_rs_per_quintal", "MSP (₹/quintal)"),
}

SOURCE_KEYWORDS = {
    "scheme":          ["scheme", "loan", "emi", "subsidy", "gst", "turnover", "finance", "financing", "grant", "mudra", "pmegp", "credit", "interest", "affordable"],
    "market_price":    ["price", "msp", "commodity", "quintal", "mandi", "market rate", "rate per quintal"],
    "agriculture":     ["crop", "irrigat", "farming", "hectare", "cultivat", "cotton", "wheat", "bajri", "groundnut", "grain", "pulses", "mustard", "castor", "soil"],
    "population":      ["literacy", "literate", "household", "census", "sc population", "st population", "male population", "female population"],
    "msme":            ["enterprise", "business", "registered", "nic code", "consultancy", "trading company", "competitor", "shop in"],
    "literacy":        ["district literacy", "rural literacy", "urban literacy"],
}

RANKING_WORDS = r"\b(highest|lowest|top|bottom|most|least|biggest|smallest|largest|max|min|maximum|minimum)\b"
TOPN_RE = re.compile(r"top\s+(\d+)")

def detect_ranking_field(query_lower):
    for field_key in RANKABLE_FIELDS:
        if field_key in query_lower:
            return field_key
    return None

def detect_source(query_lower):
    scores = {src: sum(1 for kw in kws if kw in query_lower) for src, kws in SOURCE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None

def answer(query, n=5):
    q_lower = query.lower()
    is_ranking = re.search(RANKING_WORDS, q_lower) is not None

    if is_ranking:
        field_key = detect_ranking_field(q_lower)
        if field_key:
            df, col, label = RANKABLE_FIELDS[field_key]
            ascending = bool(re.search(r"\b(lowest|least|smallest|bottom|min|minimum)\b", q_lower))
            m = TOPN_RE.search(q_lower)
            top_n = int(m.group(1)) if m else n
            name_col = "village_name" if "village_name" in df.columns else df.columns[0]
            sub = df.dropna(subset=[col]).sort_values(col, ascending=ascending).head(top_n)
            print(f"\nQUERY: {query!r}  [RANKING PATH: computed from cleaned CSV, field='{field_key}']")
            for _, row in sub.iterrows():
                extra = f", {row['taluka']} taluka" if "taluka" in df.columns else ""
                print(f"  {row[name_col]}{extra}: {label} = {row[col]}")
            return

    # Vector search path with targeted source filtering
    src = detect_source(q_lower)
    vec = model.encode([query]).tolist()
    kwargs = {"query_embeddings": vec, "n_results": n}
    
    if src == "scheme":
        kwargs["where"] = {"source": {"$in": ["real_scheme", "financial_scheme"]}}
    elif src:
        kwargs["where"] = {"source": src}
        
    res = collection.query(**kwargs)
    tag = f"VECTOR PATH, filtered to source='{src}'" if src else "VECTOR PATH, no source filter"
    print(f"\nQUERY: {query!r}  [{tag}]")
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        print(f"  [{meta.get('source')}] (dist={dist:.3f}) {doc[:160]}")

if __name__ == "__main__":
    answer("affordable loan for small dairy business")
    answer("wheat MSP price")
    answer("village with highest female literacy")