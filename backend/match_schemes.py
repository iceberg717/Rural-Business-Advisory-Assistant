import os
import pickle

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_PATH = os.path.join(CURRENT_DIR, "mehsana_graph.pkl")

G = None
if os.path.exists(GRAPH_PATH):
    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)


def match_schemes(business_type):
    if G is None:
        return []
    business_type_l = business_type.lower().strip()
    matches = []
    for n, d in G.nodes(data=True):
        if d.get("type") != "RealScheme":
            continue
        # check this scheme's SUITED_FOR business-type nodes for a text match
        for _, bt_node, ed in G.out_edges(n, data=True):
            if ed.get("relation") != "SUITED_FOR":
                continue
            bt_name = G.nodes[bt_node]["name"].lower()
            if business_type_l in bt_name or any(w in bt_name for w in business_type_l.split()):
                matches.append(d)
                break
    return matches


def print_schemes(business_type):
    matches = match_schemes(business_type)
    print(f"\n=== Government schemes matched for '{business_type}' ===")
    for m in matches:
        print(f"\n  {m['name']} ({m['scheme_id']})")
        print(f"    Target group: {m['target_group']}")
        print(f"    Max loan: {m['max_loan']} | Interest: {m['interest_rate']} | Subsidy: {m['subsidy']}")
        print(f"    Verification: {m['verification']}")


if __name__ == "__main__":
    print_schemes("dairy")
