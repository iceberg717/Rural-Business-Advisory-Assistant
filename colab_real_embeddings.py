"""
RUN THIS IN GOOGLE COLAB (free, no card needed) — NOT in the Claude sandbox,
which has no internet access to download the embedding model.

Steps to use:
1. Go to https://colab.research.google.com -> New notebook
2. Upload just ONE file from your project zip (File icon on the left sidebar
   -> Upload): chunks.jsonl (this is the only file this script actually needs —
   it already contains all the text from every dataset, pre-formatted)
3. Paste this whole script into a cell and run it (Shift+Enter)
4. It will automatically zip the result and trigger a download —
   "mehsana_vectordb_real_embeddings.zip" — no manual folder download needed.
5. Unzip it on your computer, and REPLACE the "mehsana_vectordb" folder from
   the original project zip with this new one (same folder name, just swap
   the contents). Nothing else in your pipeline (hybrid_retriever.py,
   graphrag_retriever.py, advisory_assistant.py) needs to change — they just
   read from this same folder path.

Why this works here but not in the sandbox: sentence-transformers downloads
its model weights from huggingface.co, which Colab can reach freely but the
Claude sandbox's network is locked to a small domain allowlist that excludes it.
"""

# ---- one-time installs (Colab has internet, so this just works) ----
!pip install -q sentence-transformers chromadb

import json
import chromadb
from sentence_transformers import SentenceTransformer

# all-MiniLM-L6-v2: free, small (~90MB), good quality, runs fine on Colab's free CPU
model = SentenceTransformer("all-MiniLM-L6-v2")

chunks = []
with open("chunks.jsonl") as f:
    for line in f:
        chunks.append(json.loads(line))

print(f"Loaded {len(chunks)} chunks. Encoding with real neural embeddings...")

texts = [c["text"] for c in chunks]
embeddings = model.encode(texts, batch_size=128, show_progress_bar=True, convert_to_numpy=True)

client = chromadb.PersistentClient(path="./mehsana_vectordb")
collection = client.get_or_create_collection(name="mehsana_rag", metadata={"hnsw:space": "cosine"})

BATCH = 500
for i in range(0, len(chunks), BATCH):
    batch = chunks[i:i + BATCH]
    vecs = embeddings[i:i + BATCH].tolist()
    collection.add(
        ids=[c["id"] for c in batch],
        embeddings=vecs,
        documents=[c["text"] for c in batch],
        metadatas=[c["metadata"] for c in batch],
    )
    if (i // BATCH) % 20 == 0:
        print(f"  inserted {i + len(batch)} / {len(chunks)}")

print(f"\nDone. Collection count: {collection.count()}")

# ---- quick test query to confirm quality ----
def search(query, n=5):
    qvec = model.encode([query]).tolist()
    res = collection.query(query_embeddings=qvec, n_results=n)
    print(f"\nQUERY: {query!r}")
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        print(f"  [{meta.get('source')}] (dist={dist:.3f}) {doc[:150]}")

search("affordable loan for small dairy business")   # should now match even without exact word overlap
search("cheap financing to start a milk shop")        # true paraphrase test — TF-IDF would likely miss this

# ---- zip and download the result ----
import shutil
from google.colab import files

shutil.make_archive("mehsana_vectordb_real_embeddings", "zip", "mehsana_vectordb")
print("\nZipped -> mehsana_vectordb_real_embeddings.zip")
print("Downloading now...")
files.download("mehsana_vectordb_real_embeddings.zip")
