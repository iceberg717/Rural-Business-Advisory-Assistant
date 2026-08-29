"""
Build the GraphRAG entity/relationship graph using NetworkX (pure Python,
no external downloads needed). Nodes: Village, Taluka, Crop, Enterprise,
Scheme, Commodity. Edges capture real relationships from the cleaned data.

Saved as both a pickle (for fast reload in Python) and GraphML (so it can
be opened in Gephi/Neo4j/yEd for a visual demo).
"""
import csv
import re
import pickle
import networkx as nx

G = nx.MultiDiGraph()

def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")

def add_village_node(vname, taluka, **attrs):
    vid = f"village::{norm(vname)}::{norm(taluka)}"
    if not G.has_node(vid):
        G.add_node(vid, type="Village", name=vname, taluka=taluka, **attrs)
    return vid

def add_taluka_node(taluka):
    tid = f"taluka::{norm(taluka)}"
    if not G.has_node(tid):
        G.add_node(tid, type="Taluka", name=taluka)
    return tid

def add_crop_node(crop):
    crop = crop.strip()
    if not crop or crop.upper() in ("", "NA", "NONE"):
        return None
    cid = f"crop::{norm(crop)}"
    if not G.has_node(cid):
        G.add_node(cid, type="Crop", name=crop)
    return cid

def add_scheme_node(scheme_name, sector):
    sid = f"scheme::{norm(scheme_name)}::{norm(sector)}"
    if not G.has_node(sid):
        G.add_node(sid, type="Scheme", name=scheme_name, sector=sector)
    return sid

def add_sector_node(sector):
    sid = f"sector::{norm(sector)}"
    if not G.has_node(sid):
        G.add_node(sid, type="Sector", name=sector)
    return sid

def add_commodity_node(commodity, group):
    cid = f"commodity::{norm(commodity)}"
    if not G.has_node(cid):
        G.add_node(cid, type="Commodity", name=commodity, group=group)
    return cid

def add_enterprise_node(name, pincode, idx):
    eid = f"enterprise::{idx}"
    G.add_node(eid, type="Enterprise", name=name, pincode=pincode)
    return eid

def add_activity_node(desc):
    if not desc:
        return None
    aid = f"activity::{norm(desc)[:60]}"
    if not G.has_node(aid):
        G.add_node(aid, type="Activity", name=desc)
    return aid

# ---------- Population + Taluka ----------
with open("population_clean.csv") as f:
    for r in csv.DictReader(f):
        tid = add_taluka_node(r["taluka"])
        vid = add_village_node(r["village_name"], r["taluka"],
                                population=r["total_p"], male=r["total_m"], female=r["total_f"],
                                households=r["no_hh"], literate=r["p_lit"])
        G.add_edge(vid, tid, relation="LOCATED_IN")

# ---------- Agriculture: crops + income (merge into existing village nodes when possible) ----------
with open("agriculture_clean.csv") as f:
    for r in csv.DictReader(f):
        taluka = r["taluka"]
        if taluka.startswith(("AMBIGUOUS", "UNMATCHED")):
            continue  # skip graph edges for unresolved villages — don't guess in the graph
        vid = add_village_node(r["village_name"], taluka,
                                area_ha=r["area_ha"], income=r["tot_income"])
        tid = add_taluka_node(taluka)
        G.add_edge(vid, tid, relation="LOCATED_IN")
        for crop_field in ("main_crop_1", "main_crop_2", "main_crop_3"):
            crop = r[crop_field]
            cid = add_crop_node(crop)
            if cid:
                G.add_edge(vid, cid, relation="GROWS")

# ---------- Financial schemes: Scheme -> Sector, Scheme -> Taluka ----------
with open("financial_clean.csv") as f:
    for r in csv.DictReader(f):
        sid = add_scheme_node(r["government_or_finance_scheme"], r["business_sector"])
        sec_id = add_sector_node(r["business_sector"])
        tid = add_taluka_node(r["taluka"])
        G.add_edge(sid, sec_id, relation="APPLIES_TO_SECTOR")
        G.add_edge(sid, tid, relation="AVAILABLE_IN")
        G.nodes[sid]["loan_amount"] = r["indicative_loan_amount_inr"]
        G.nodes[sid]["emi"] = r["estimated_monthly_emi_inr"]
        G.nodes[sid]["business_type"] = r["business_type"]

# ---------- Market prices: Commodity nodes ----------
with open("market_prices_clean.csv") as f:
    for r in csv.DictReader(f):
        cid = add_commodity_node(r["commodity"], r["commodity_group"])
        G.nodes[cid]["msp"] = r["msp_rs_per_quintal"]
        G.nodes[cid]["price"] = r["price_rs_per_quintal"]

# link Crop nodes to Commodity nodes where names roughly match (helps cross-domain traversal:
# village -> grows -> crop -> is_a -> commodity -> priced_at -> market price)
crop_nodes = {n: d for n, d in G.nodes(data=True) if d.get("type") == "Crop"}
commodity_nodes = {n: d for n, d in G.nodes(data=True) if d.get("type") == "Commodity"}
linked = 0
for cnid, cdata in crop_nodes.items():
    cname_norm = norm(cdata["name"])
    for comid, comdata in commodity_nodes.items():
        com_norm = norm(comdata["name"])
        if cname_norm in com_norm or com_norm.split("_")[0] in cname_norm:
            G.add_edge(cnid, comid, relation="IS_A")
            linked += 1

# ---------- MSME: Enterprise -> Activity (skip pincode->village mapping, no reliable key) ----------
with open("msme_clean.csv") as f:
    for i, r in enumerate(csv.DictReader(f)):
        eid = add_enterprise_node(r["enterprise_name"], r["pincode"], i)
        G.nodes[eid]["taluka"] = r.get("taluka", "")
        if r.get("taluka"):
            tid = add_taluka_node(r["taluka"])
            G.add_edge(eid, tid, relation="LOCATED_IN")
        for desc in r["activity_descriptions"].split(";"):
            desc = desc.strip()
            aid = add_activity_node(desc)
            if aid:
                G.add_edge(eid, aid, relation="ENGAGES_IN")

# ---------- Real government schemes: Scheme -> "best for" business type (as loose text tags) ----------
with open("real_schemes_clean.csv") as f:
    for r in csv.DictReader(f):
        sid = f"realscheme::{norm(r['scheme_id'])}"
        G.add_node(sid, type="RealScheme", name=r["scheme_name"], scheme_id=r["scheme_id"],
                   target_group=r["target_group"], max_loan=r["max_loan_amount"],
                   interest_rate=r["interest_rate"], subsidy=r["subsidy"],
                   verification=r["verification_status"])
        for biz in r["best_for_businesses"].split(";"):
            biz = biz.strip()
            if not biz:
                continue
            bid = f"businesstype::{norm(biz)[:40]}"
            if not G.has_node(bid):
                G.add_node(bid, type="BusinessType", name=biz)
            G.add_edge(sid, bid, relation="SUITED_FOR")

print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
from collections import Counter
node_types = Counter(d.get("type") for _, d in G.nodes(data=True))
for t, n in node_types.most_common():
    print(f"  {t}: {n}")
edge_types = Counter(d.get("relation") for _, _, d in G.edges(data=True))
print("Edge types:")
for t, n in edge_types.most_common():
    print(f"  {t}: {n}")
print(f"Crop-Commodity links: {linked}")

with open("mehsana_graph.pkl", "wb") as f:
    pickle.dump(G, f)

nx.write_graphml(G, "mehsana_graph.graphml")
print("\nSaved: mehsana_graph.pkl (Python) and mehsana_graph.graphml (Gephi/Neo4j/yEd viewer)")
