import pickle
# import networkx as nx

with open("mehsana_graph.pkl", "rb") as f:
    G = pickle.load(f)

def multihop_example_1():
    """Villages in Kheralu taluka that grow cotton, and what scheme sector could serve them."""
    taluka_id = "taluka::kheralu"
    cotton_id = "crop::cotton"
    print(f"\n1-HOP: Villages LOCATED_IN Kheralu taluka")
    villages = [u for u, v, d in G.in_edges(taluka_id, data=True) if d.get("relation") == "LOCATED_IN"]
    print(f"  found {len(villages)} villages")

    print(f"\n2-HOP: ...of those, which GROW cotton")
    cotton_villages = []
    seen = set()
    for v in villages:
        if v in seen:
            continue
        for _, crop, d in G.out_edges(v, data=True):
            if d.get("relation") == "GROWS" and crop == cotton_id:
                cotton_villages.append(v)
                seen.add(v)
                break
    for v in cotton_villages[:8]:
        print(f"  - {G.nodes[v]['name']} (pop {G.nodes[v].get('population', '?')})")
    print(f"  total: {len(cotton_villages)} cotton-growing villages in Kheralu")

    print(f"\n3-HOP: cotton -> IS_A -> which market commodity, and its current price")
    for _, com, d in G.out_edges(cotton_id, data=True):
        if d.get("relation") == "IS_A":
            cdata = G.nodes[com]
            print(f"  Cotton crop maps to commodity '{cdata['name']}': MSP ₹{cdata.get('msp')}, price ₹{cdata.get('price')}/quintal")

def multihop_example_2():
    """Which scheme sectors are available in Unjha taluka."""
    taluka_id = "taluka::unjha"
    print(f"\nSchemes AVAILABLE_IN Unjha taluka:")
    schemes = [u for u, v, d in G.in_edges(taluka_id, data=True) if d.get("relation") == "AVAILABLE_IN"]
    for s in schemes:
        sd = G.nodes[s]
        print(f"  - {sd['name']} ({sd.get('business_type')}, sector: {sd.get('sector')}) — loan ₹{sd.get('loan_amount')}, EMI ₹{sd.get('emi')}")

def multihop_example_3():
    """What activities do enterprises engage in, sample."""
    print(f"\nSample: Enterprise -> ENGAGES_IN -> Activity (shows the 63k MSME layer is graph-connected too)")
    ent_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "Enterprise"][:3]
    for e in ent_nodes:
        ed = G.nodes[e]
        acts = [G.nodes[a]["name"] for _, a, d in G.out_edges(e, data=True) if d.get("relation") == "ENGAGES_IN"]
        print(f"  {ed['name']}: {acts}")

if __name__ == "__main__":
    multihop_example_1()
    multihop_example_2()
    multihop_example_3()