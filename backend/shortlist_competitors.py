"""
Competitor shortlisting for a given business type + taluka.

Two-layer approach:
  1. KEYWORD FILTER (the actual shortlist) — exact substring match against
     activity_descriptions, scoped to the user's taluka. Complete and precise:
     every real dairy business in that taluka, nothing vaguely-related mixed in.
  2. VECTOR SIMILARITY (secondary "related businesses") — search for
     businesses that don't contain the exact keyword but are semantically close
     (e.g. "milk product retail", "ghee trading") — a discovery layer.
"""
import csv
import chromadb
from sentence_transformers import SentenceTransformer

# Load model & client
client = chromadb.PersistentClient(path="./mehsana_vectordb")
collection = client.get_or_create_collection(name="mehsana_rag", metadata={"hnsw:space": "cosine"})
model = SentenceTransformer("all-MiniLM-L6-v2")

# business type -> keywords to match in activity_descriptions (extend as needed)
CATEGORY_KEYWORDS = {
    "dairy": ["dairy", "milk", "ghee", "paneer", "curd", "butter", "khoya", "pashupalan"],
    "retail": ["retail", "grocery", "general store", "kirana", "shop", "parlour", "super market"],
    "food processing": ["food processing", "spice", "masala", "flour mill", "oil mill",
                         "pickle", "snack", "bakery", "papads", "edible"],
    "textile": ["textile", "weaving", "garment", "tailoring", "yarn", "cotton", "cloth", "hosiery"],
    "computer/it": ["computer", "software", "it services", "consultancy"],
    "repair": ["repair", "servicing", "maintenance"],
    "agri-business": ["seed", "fertilizer", "agri", "farming", "pesticide", "mandi"],
}


def load_msme():
    with open("msme_clean.csv", mode="r", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


_MSME_ROWS = load_msme()


def shortlist_competitors(business_type, taluka=None, top_n=10):
    business_type_l = business_type.lower().strip()
    keywords = CATEGORY_KEYWORDS.get(business_type_l)
    if not keywords:
        # fall back: treat the business_type itself as the keyword
        keywords = [business_type_l]

    # ---- Layer 1: keyword filter (the hard shortlist) ----
    exact_matches = []
    for r in _MSME_ROWS:
        if taluka and r.get("taluka", "").lower() != taluka.lower():
            continue
        desc = r.get("activity_descriptions", "").lower()
        if any(kw in desc for kw in keywords):
            exact_matches.append(r)

    # ---- Layer 2: vector similarity (related/adjacent businesses) ----
    query_text = f"{business_type} business activities"
    vec = model.encode([query_text]).tolist()
    where_filter = {"source": "msme"}
    if taluka:
        where_filter = {"$and": [{"source": "msme"}, {"taluka": taluka}]}

    try:
        res = collection.query(query_embeddings=vec, n_results=top_n * 3, where=where_filter)
        exact_names = {r["enterprise_name"] for r in exact_matches}
        related = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            name_line = doc.split(",")[0].replace("Enterprise: ", "")
            if name_line in exact_names:
                continue
            related.append((doc, dist))
    except Exception:
        related = []

    return exact_matches, related[:5]


def print_shortlist(business_type, taluka=None):
    exact, related = shortlist_competitors(business_type, taluka)
    print(f"\n=== Competitor shortlist: '{business_type}' businesses in {taluka or 'all talukas'} ===")
    print(f"\nEXACT MATCHES (keyword filter — the real shortlist): {len(exact)} found")
    for r in exact[:15]:
        print(f"  - {r['enterprise_name']} | {r['activity_descriptions'][:80]}")
    if len(exact) > 15:
        print(f"  ... and {len(exact) - 15} more")

    if related:
        print(f"\nRELATED/ADJACENT (vector similarity — discovery layer, not exact matches):")
        for doc, dist in related:
            print(f"  - (dist={dist:.3f}) {doc[:110]}")


if __name__ == "__main__":
    print_shortlist("dairy", "Kadi")
    print_shortlist("retail", "Unjha")