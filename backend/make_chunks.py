"""
Step: Chunk generation.
Converts each cleaned CSV row into a natural-language sentence (a "chunk"),
tagged with metadata for filtering later. Writes one JSONL file: chunks.jsonl
Each line: {"id": ..., "text": ..., "metadata": {...}}
"""
import csv, json

def fnum(x, default="unknown"):
    try:
        if x in (None, "", "None"):
            return default
        return f"{float(x):,.0f}"
    except Exception:
        return x or default

chunks = []
cid = 0

# ---------- Population chunks ----------
with open("population_clean.csv") as f:
    for r in csv.DictReader(f):
        cid += 1
        text = (
            f"Village {r['village_name']}, {r['taluka']} taluka, Mehsana district. "
            f"Population {fnum(r['total_p'])} (male {fnum(r['total_m'])}, female {fnum(r['total_f'])}), "
            f"{fnum(r['no_hh'])} households. Literate population {fnum(r['p_lit'])}. "
            f"SC population {fnum(r['p_sc'])}, ST population {fnum(r['p_st'])}. "
            f"Total workers {fnum(r['tot_work_p'])} (male {fnum(r['tot_work_m'])}, female {fnum(r['tot_work_f'])}). "
            f"Cultivators {fnum(r['main_cl_p'])}, agricultural labourers {fnum(r['main_al_p'])}."
        )
        chunks.append({
            "id": f"pop_{cid}",
            "text": text,
            "metadata": {"source": "population", "village": r["village_name"], "taluka": r["taluka"]},
        })

# ---------- Agriculture chunks ----------
with open("agriculture_clean.csv") as f:
    for r in csv.DictReader(f):
        cid += 1
        text = (
            f"Village {r['village_name']} (nearest town {r['near_town']}), taluka: {r['taluka']}. "
            f"Area {r['area_ha']} hectares, {fnum(r['tot_hh'])} households, population {fnum(r['tot_p'])}. "
            f"Main crops grown: {r['main_crop_1']}, {r['main_crop_2']}, {r['main_crop_3']}. "
            f"Total irrigated area {r['tot_irrigated']} ha, unirrigated {r['un_irrigated']} ha. "
            f"Annual income ₹{fnum(r['tot_income'])}, annual expense ₹{fnum(r['tot_expense'])}. "
            f"Bank facility available: {'yes' if r['bank_facility'] not in ('', '3') else 'no'}."
        )
        chunks.append({
            "id": f"agri_{cid}",
            "text": text,
            "metadata": {"source": "agriculture", "village": r["village_name"], "taluka": r["taluka"]},
        })

# ---------- MSME chunks (63k rows — keep it lean) ----------
with open("msme_clean.csv") as f:
    for r in csv.DictReader(f):
        cid += 1
        taluka_str = f" Taluka: {r['taluka']}." if r.get("taluka") else ""
        text = (
            f"Enterprise: {r['enterprise_name']}, registered {r['registration_date']} in "
            f"{r['district']}, pincode {r['pincode']}.{taluka_str} Address: {r['address']}. "
            f"Activities: {r['activity_descriptions']}."
        )
        chunks.append({
            "id": f"msme_{cid}",
            "text": text,
            "metadata": {"source": "msme", "pincode": r["pincode"], "nic_codes": r["nic_codes"],
                         "taluka": r.get("taluka", "")},
        })

# ---------- Financial / Scheme chunks ----------
with open("financial_clean.csv") as f:
    for r in csv.DictReader(f):
        cid += 1
        text = (
            f"Scheme: {r['government_or_finance_scheme']}, for {r['business_type']} "
            f"({r['business_sector']} sector, {r['msme_category']} category) in {r['taluka']} taluka. "
            f"Annual turnover ₹{r['annual_turnover_inr']}, GST rate {r['gst_rate_percent']}%. "
            f"Indicative loan amount ₹{r['indicative_loan_amount_inr']} at {r['indicative_interest_rate_percent_pa']}% p.a. "
            f"interest, potential subsidy {r['potential_interest_subsidy_percent']}%, "
            f"tenure {r['loan_tenure_years']} years, estimated EMI ₹{r['estimated_monthly_emi_inr']}."
        )
        chunks.append({
            "id": f"fin_{cid}",
            "text": text,
            "metadata": {"source": "financial_scheme", "taluka": r["taluka"], "sector": r["business_sector"]},
        })

# ---------- Market price chunks ----------
with open("market_prices_clean.csv") as f:
    for r in csv.DictReader(f):
        cid += 1
        text = (
            f"{r['commodity']} ({r['commodity_group']}): MSP ₹{r['msp_rs_per_quintal']}/quintal, "
            f"market price ₹{r['price_rs_per_quintal']}/quintal as of {r['price_date']}."
        )
        chunks.append({
            "id": f"price_{cid}",
            "text": text,
            "metadata": {"source": "market_price", "commodity": r["commodity"], "group": r["commodity_group"]},
        })

# ---------- Literacy summary chunks ----------
with open("literacy_summary_clean.csv") as f:
    for r in csv.DictReader(f):
        cid += 1
        text = (
            f"Mehsana district {r['area_type']} area (2011 Census): population {r['population']}, "
            f"male {r['male_population']}, female {r['female_population']}, literate {r['literate']}, "
            f"literacy rate {r['literacy_rate_percent']}%."
        )
        chunks.append({
            "id": f"lit_{cid}",
            "text": text,
            "metadata": {"source": "literacy", "area_type": r["area_type"]},
        })

# ---------- Real government scheme chunks ----------
with open("real_schemes_clean.csv") as f:
    for r in csv.DictReader(f):
        cid += 1
        text = (
            f"Government Scheme: {r['scheme_name']} ({r['scheme_id']}). "
            f"Target group: {r['target_group']}. Project cost range: {r['project_cost_range']}. "
            f"Max loan amount: {r['max_loan_amount']}. Margin requirement: {r['margin_requirement']}. "
            f"Interest rate: {r['interest_rate']}. Tenure: {r['tenure_years']}. "
            f"Subsidy: {r['subsidy']}. Best suited for: {r['best_for_businesses']}. "
            f"Verification status: {r['verification_status']}."
        )
        chunks.append({
            "id": f"scheme_{cid}",
            "text": text,
            "metadata": {"source": "real_scheme", "scheme_id": r["scheme_id"],
                         "best_for": r["best_for_businesses"]},
        })

with open("chunks.jsonl", "w") as f:
    for c in chunks:
        f.write(json.dumps(c) + "\n")

print(f"Total chunks generated: {len(chunks)}")
from collections import Counter
by_source = Counter(c["metadata"]["source"] for c in chunks)
for src, n in by_source.items():
    print(f"  {src}: {n}")

print("\nSample chunks:")
for c in chunks[:2] + chunks[600:602] + chunks[-3:]:
    print(" -", c["text"][:150])
