"""
Resolve AMBIGUOUS agriculture-village-to-taluka matches by comparing population
counts against each candidate taluka's village of the same name. Same name AND
near-identical population is strong evidence of the correct match.
Villages that don't resolve confidently stay flagged for manual review.
"""
import csv
import re

def norm(name):
    if name is None:
        return ""
    n = str(name).strip().lower()
    n = re.sub(r"\(.*?\)", "", n)
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    return n

with open("population_clean.csv") as f:
    pop_rows = list(csv.DictReader(f))

pop_lookup = {}
for r in pop_rows:
    key = r["village_name_norm"]
    pop_lookup.setdefault(key, []).append(r)

with open("agriculture_clean.csv") as f:
    agri_rows = list(csv.DictReader(f))

resolved, still_unresolved = 0, 0
for r in agri_rows:
    if not r["taluka"].startswith("AMBIGUOUS"):
        continue
    key = r["village_name_norm"]
    candidates = pop_lookup.get(key, [])
    try:
        agri_pop = float(r["tot_p"])
    except (ValueError, TypeError):
        continue
    best, best_diff = None, None
    for c in candidates:
        try:
            c_pop = float(c["total_p"])
        except (ValueError, TypeError):
            continue
        diff_pct = abs(c_pop - agri_pop) / max(agri_pop, 1)
        if best_diff is None or diff_pct < best_diff:
            best, best_diff = c, diff_pct
    if best is not None and best_diff <= 0.08:  # within 8% population match
        r["taluka"] = best["taluka"]
        r["taluka_resolved_by"] = "population_match"
        resolved += 1
    else:
        r["taluka_resolved_by"] = ""
        still_unresolved += 1

# also stamp non-ambiguous rows with empty resolved_by for consistent schema
for r in agri_rows:
    if "taluka_resolved_by" not in r:
        r["taluka_resolved_by"] = ""

with open("agriculture_clean.csv", "w", newline="") as f:
    fieldnames = list(agri_rows[0].keys())
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(agri_rows)

print(f"Resolved via population match: {resolved}")
print(f"Still unresolved (left as AMBIGUOUS): {still_unresolved}")

# recompute overall match stats
n_matched = sum(1 for r in agri_rows if not r["taluka"].startswith(("AMBIGUOUS", "UNMATCHED")))
n_ambig = sum(1 for r in agri_rows if r["taluka"].startswith("AMBIGUOUS"))
n_unmatch = sum(1 for r in agri_rows if r["taluka"] == "UNMATCHED")
print(f"\nFinal: matched {n_matched}, still ambiguous {n_ambig}, unmatched {n_unmatch}, total {len(agri_rows)}")
