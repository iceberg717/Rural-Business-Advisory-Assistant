"""Flatten the real, sourced government schemes JSON into a clean CSV."""
import json, csv

with open("1788016168329_Schemes_data.json") as f:
    data = json.load(f)

schemes = data["sih_project_recommended_schemes"]["schemes"]

rows = []
for s in schemes:
    rows.append({
        "scheme_id": s["scheme_id"],
        "scheme_name": s["scheme_name"],
        "target_group": s.get("target_group", ""),
        "project_cost_range": s.get("project_cost_range", ""),
        "margin_requirement": s.get("margin_requirement", ""),
        "max_loan_amount": s.get("max_loan_amount", ""),
        "interest_rate": s.get("interest_rate", ""),
        "tenure_years": s.get("tenure_years", ""),
        "moratorium_months": s.get("moratorium_months", ""),
        "subsidy": s.get("subsidy", ""),
        "collateral_required": s.get("collateral_required", ""),
        "best_for_businesses": ";".join(s.get("best_for_businesses", [])),
        "official_portal": s.get("official_portal", s.get("official_contact", "")),
        "verification_status": s.get("documentation_status", ""),
    })

with open("real_schemes_clean.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"Flattened {len(rows)} real government schemes -> real_schemes_clean.csv")
for r in rows:
    print(f"  - {r['scheme_id']}: best for {r['best_for_businesses']}")
