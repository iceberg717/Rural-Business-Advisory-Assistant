"""
True GraphRAG retrieval: vector search finds the most relevant seed node(s),
then the graph is traversed outward from those seeds to pull connected context
(nearby entities, relationships) that a pure similarity search would miss.

Pipeline per query:
  1. Detect ranking/computation queries -> answer directly from CSVs (unchanged)
  2. Otherwise: vector search (TF-IDF) -> top-k chunks -> map each chunk to its
     graph node -> traverse N hops out from each seed -> collect connected
     nodes/edges -> assemble final context (seed facts + graph-connected facts)
"""
import re
import pickle
import pandas as pd
import chromadb
import networkx as nx

# ---------- load everything ----------
with open("embedder.pkl", "rb") as f:
    _e = pickle.load(f)
vectorizer, svd = _e["vectorizer"], _e["svd"]

client = chromadb.PersistentClient(path="./mehsana_vectordb")
collection = client.get_or_create_collection(name="mehsana_rag", metadata={"hnsw:space": "cosine"})

with open("mehsana_graph.pkl", "rb") as f:
    G = pickle.load(f)

population_df = pd.read_csv("population_clean.csv")
agriculture_df = pd.read_csv("agriculture_clean.csv")
financial_df = pd.read_csv("financial_clean.csv")
prices_df = pd.read_csv("market_prices_clean.csv")

RANKABLE_FIELDS = {
    "population": (population_df, "total_p", "population"),
    "literacy": (population_df, "p_lit", "literate population"),
    "female literacy": (population_df, "f_lit", "female literate population"),
    "male literacy": (population_df, "m_lit", "male literate population"),
    "households": (population_df, "no_hh", "households"),
    "irrigated area": (agriculture_df, "tot_irrigated", "irrigated area (ha)"),
    "income": (agriculture_df, "tot_income", "annual income (₹)"),
    "loan amount": (financial_df, "indicative_loan_amount_inr", "loan amount (₹)"),
    "emi": (financial_df, "estimated_monthly_emi_inr", "EMI (₹)"),
    "price": (prices_df, "price_rs_per_quintal", "market price (₹/quintal)"),
    "msp": (prices_df, "msp_rs_per_quintal", "MSP (₹/quintal)"),
}
SOURCE_KEYWORDS = {
    "market_price": ["price", "msp", "commodity", "quintal", "mandi", "market rate"],
    "financial_scheme": ["scheme", "loan", "emi", "subsidy", "gst", "turnover", "finance"],
    "msme": ["enterprise", "business", "registered", "nic code", "consultancy", "trading company"],
    "agriculture": ["crop", "irrigat", "farming", "hectare", "cultivat", "cotton", "wheat", "bajri",
                     "groundnut", "grain", "pulses"],
    "population": ["literacy", "literate", "household", "census", "sc population", "st population"],
}
RANKING_WORDS = r"\b(highest|lowest|top|bottom|most|least|biggest|smallest|largest|max|min|maximum|minimum)\b"
TOPN_RE = re.compile(r"top\s+(\d+)")


def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")


def chunk_to_node_id(meta):
    """Map a retrieved chunk's metadata back to its node in the graph, if it has one."""
    src = meta.get("source")
    if src in ("population", "agriculture"):
        village, taluka = meta.get("village"), meta.get("taluka")
        if village and taluka and not str(taluka).startswith(("AMBIGUOUS", "UNMATCHED")):
            return f"village::{norm(village)}::{norm(taluka)}"
    if src == "market_price":
        commodity = meta.get("commodity")
        if commodity:
            return f"commodity::{norm(commodity)}"
    return None  # financial_scheme/msme chunks don't carry a clean unique key in metadata alone


def expand_from_node(node_id, hops=2, max_per_hop=6):
    """Traverse outward (and inward) from a seed node, collecting connected facts."""
    if node_id not in G:
        return []
    facts = []
    frontier = {node_id}
    visited = {node_id}
    for hop in range(hops):
        next_frontier = set()
        for n in frontier:
            edges = list(G.out_edges(n, data=True))[:max_per_hop] + list(G.in_edges(n, data=True))[:max_per_hop]
            for u, v, d in edges:
                other = v if u == n else u
                if other in visited:
                    continue
                visited.add(other)
                next_frontier.add(other)
                rel = d.get("relation", "?")
                odata = G.nodes[other]
                facts.append({
                    "hop": hop + 1,
                    "relation": rel,
                    "node_type": odata.get("type"),
                    "name": odata.get("name"),
                    "extra": {k: v2 for k, v2 in odata.items() if k not in ("type", "name")},
                })
        frontier = next_frontier
        if not frontier:
            break
    return facts


def detect_ranking_field(q):
    for k in RANKABLE_FIELDS:
        if k in q:
            return k
    return None


def detect_source(q):
    scores = {s: sum(1 for kw in kws if kw in q) for s, kws in SOURCE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def graphrag_answer(query, n=5, hops=2):
    q_lower = query.lower()

    # ranking path unchanged
    if re.search(RANKING_WORDS, q_lower):
        field_key = detect_ranking_field(q_lower)
        if field_key:
            df, col, label = RANKABLE_FIELDS[field_key]
            ascending = bool(re.search(r"\b(lowest|least|smallest|bottom|min|minimum)\b", q_lower))
            m = TOPN_RE.search(q_lower)
            top_n = int(m.group(1)) if m else n
            name_col = "village_name" if "village_name" in df.columns else df.columns[0]
            sub = df.dropna(subset=[col]).sort_values(col, ascending=ascending).head(top_n)
            print(f"\nQUERY: {query!r}  [RANKING PATH]")
            for _, row in sub.iterrows():
                extra = f", {row['taluka']} taluka" if "taluka" in df.columns else ""
                print(f"  {row[name_col]}{extra}: {label} = {row[col]}")
            return

    # vector search -> seed nodes -> graph expansion
    src = detect_source(q_lower)
    vec = svd.transform(vectorizer.transform([query])).tolist()
    kwargs = {"query_embeddings": vec, "n_results": n}
    if src:
        kwargs["where"] = {"source": src}
    res = collection.query(**kwargs)

    print(f"\nQUERY: {query!r}  [GRAPHRAG PATH: vector seed -> {hops}-hop graph expansion]")
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        print(f"\n  SEED [{meta.get('source')}] (dist={dist:.3f}): {doc[:140]}")
        node_id = chunk_to_node_id(meta)
        if not node_id:
            print(f"    (no graph node mapped for this chunk's source type)")
            continue
        facts = expand_from_node(node_id, hops=hops)
        if not facts:
            print(f"    (seed node found in graph but no connected facts)")
        for fct in facts[:10]:
            extra_str = ", ".join(f"{k}={v}" for k, v in fct["extra"].items() if v not in (None, ""))
            print(f"    hop{fct['hop']} --{fct['relation']}--> [{fct['node_type']}] {fct['name']} ({extra_str})")


if __name__ == "__main__":
    graphrag_answer("cotton farming village")
    graphrag_answer("wheat price")
    graphrag_answer("village Chansol")
