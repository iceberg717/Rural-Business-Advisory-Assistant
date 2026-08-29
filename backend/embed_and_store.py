"""
Embed all chunks using TF-IDF (scikit-learn) — no external model download required,
which matters since this sandbox's network is locked to a domain allowlist that
doesn't include Chroma's/HuggingFace's default model hosts.
TF-IDF works well here because the domain vocabulary (village names, crop names,
scheme names, NIC activity descriptions) is distinctive and keyword-driven.
Vectors are reduced with TruncatedSVD to keep them dense + a manageable size.
"""
import json
import numpy as np
import chromadb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import pickle

chunks = []
with open("chunks.jsonl") as f:
    for line in f:
        chunks.append(json.loads(line))

texts = [c["text"] for c in chunks]
print(f"Fitting TF-IDF on {len(texts)} chunks...")

vectorizer = TfidfVectorizer(max_features=20000, stop_words="english", ngram_range=(1, 2))
tfidf_matrix = vectorizer.fit_transform(texts)
print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")

n_components = 256
svd = TruncatedSVD(n_components=n_components, random_state=42)
dense_vectors = svd.fit_transform(tfidf_matrix)
print(f"Reduced to dense vectors: {dense_vectors.shape}, explained variance: {svd.explained_variance_ratio_.sum():.3f}")

with open("embedder.pkl", "wb") as f:
    pickle.dump({"vectorizer": vectorizer, "svd": svd}, f)

client = chromadb.PersistentClient(path="./mehsana_vectordb")
collection = client.get_or_create_collection(name="mehsana_rag", metadata={"hnsw:space": "cosine"})

BATCH = 500
for i in range(0, len(chunks), BATCH):
    batch = chunks[i:i + BATCH]
    vecs = dense_vectors[i:i + BATCH].tolist()
    collection.add(
        ids=[c["id"] for c in batch],
        embeddings=vecs,
        documents=[c["text"] for c in batch],
        metadatas=[c["metadata"] for c in batch],
    )
    if (i // BATCH) % 20 == 0:
        print(f"  inserted {i + len(batch)} / {len(chunks)}")

print(f"\nDone. Collection count: {collection.count()}")
