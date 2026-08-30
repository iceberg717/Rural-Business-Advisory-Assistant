"""
Business Advisory Assistant — orchestrates schemes + competitors + market
context into one advisory report, given a business idea + location + investment budget.

Features:
  - 3-Way Entity Extraction: Business Category, Mehsana Taluka, Investment/Budget Amount.
  - Capital Adequacy Benchmarking: Compares user budget with industry standard setup costs.
  - Smart Underfunded Handling: Recommends local lower-capital alternatives & calculated government loan subsidies.
  - Hybrid LLM & Template Engine: Uses Gemini with automatic deterministic local fallback.
"""
import os
import sys
import pickle
import re

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from match_schemes import match_schemes
    from shortlist_competitors import shortlist_competitors, CATEGORY_KEYWORDS
    from geoapify_integration import fetch_live_competitors_from_geoapify
except ImportError:
    from backend.match_schemes import match_schemes
    from backend.shortlist_competitors import shortlist_competitors, CATEGORY_KEYWORDS
    from backend.geoapify_integration import fetch_live_competitors_from_geoapify

GRAPH_PATH = os.path.join(CURRENT_DIR, "mehsana_graph.pkl")
G = None
if os.path.exists(GRAPH_PATH):
    try:
        with open(GRAPH_PATH, "rb") as f:
            G = pickle.load(f)
    except Exception as e:
        print(f"Warning: Failed to load graph from {GRAPH_PATH}: {e}")

MEHSANA_TALUKAS = [
    "Becharaji", "Kadi", "Kheralu", "Mahesana", "Satlasana", "Unjha", "Vadnagar", "Vijapur", "Visnagar"
]

BUDGET_PRESETS = [
    {"label": "Micro (< ₹1 Lakh)", "value": "₹1 Lakh", "amount": 100000},
    {"label": "₹1 - 3 Lakhs (Small Unit)", "value": "₹3 Lakhs", "amount": 300000},
    {"label": "₹3 - 5 Lakhs (PMEGP Micro)", "value": "₹5 Lakhs", "amount": 500000},
    {"label": "₹5 - 10 Lakhs (Mudra Tarun)", "value": "₹10 Lakhs", "amount": 1000000},
    {"label": "₹10 - 25 Lakhs (Medium MSME)", "value": "₹25 Lakhs", "amount": 2500000},
    {"label": "₹25+ Lakhs (Commercial Plant)", "value": "₹50 Lakhs", "amount": 5000000}
]

INDUSTRY_CAPITAL_BENCHMARKS = {
    "dairy_processing": {
        "keywords": ["dairy processing", "milk processing", "pasteurization", "cheese plant", "ice cream plant", "ghee plant", "dairy plant"],
        "min_capital": 800000,
        "recommended_capital": 1800000,
        "industry_name": "Commercial Dairy & Milk Processing Plant",
        "alternatives": [
            {"name": "Milk Collection & Chilling Center", "min_budget": 100000, "desc": "Collection center with digital fat testing and milk cans supplying to Dudhsagar / Amul cooperative."},
            {"name": "Value-Added Ghee & Chhas Micro-Unit", "min_budget": 150000, "desc": "Small-scale artisan butter, buttermilk and traditional bilona ghee packaging unit."},
            {"name": "Cattle Feed & Mineral Mixture Distribution", "min_budget": 80000, "desc": "Retail agency supplying quality balanced cattle feed directly to local dairy farmers."}
        ]
    },
    "dairy": {
        "keywords": ["dairy", "dairy farm", "cow", "buffalo", "cattle", "milk shop", "dairy unit", "dairy business"],
        "min_capital": 150000,
        "recommended_capital": 400000,
        "industry_name": "Dairy Cattle Farming (2-4 HF / Gir Cows)",
        "alternatives": [
            {"name": "Single Cow Micro-Dairy Unit", "min_budget": 75000, "desc": "Start with 1 high-yielding Gir/HF cow with cooperative milk supply linkage."},
            {"name": "Vermicompost Production Unit", "min_budget": 40000, "desc": "Low-investment high-margin organic fertilizer production using farm cow dung."},
            {"name": "Silage & Green Fodder Supply", "min_budget": 60000, "desc": "Contract green fodder chopping and bagged silage supply to local cattle owners."}
        ]
    },
    "textile": {
        "keywords": ["textile", "weaving", "powerloom", "cloth", "garment", "fabric", "spinning", "handloom"],
        "min_capital": 350000,
        "recommended_capital": 900000,
        "industry_name": "Textile Weaving & Powerloom Enterprise",
        "alternatives": [
            {"name": "Readymade Garment & Tailoring Jobwork", "min_budget": 75000, "desc": "Boutique tailoring, uniform stitching and alterations micro-unit."},
            {"name": "Textile Trading & Saree / Dress Agency", "min_budget": 100000, "desc": "Direct wholesale sourcing with doorstep rural retail distribution."},
            {"name": "Embroidery & Screen Printing Unit", "min_budget": 120000, "desc": "Computerized embroidery and traditional ethnic printing service for local weavers."}
        ]
    },
    "food_processing": {
        "keywords": ["spice", "flour", "food processing", "oil mill", "besan", "pickle", "snacks", "bakery", "namkeen", "masala"],
        "min_capital": 200000,
        "recommended_capital": 650000,
        "industry_name": "Commercial Spice & Food Processing Mill",
        "alternatives": [
            {"name": "Micro Flour & Spices Grinding Mill (Ghar Ghanti)", "min_budget": 60000, "desc": "Small pulverizer grinding cumin (jeera), coriander, chili, and wheat for local residents."},
            {"name": "Papad, Khakhra & Pickle Cottage Enterprise", "min_budget": 40000, "desc": "Home-scale authentic Gujarati snacks with local retail packaging."},
            {"name": "Unjha Jeera / Fennel Retail Packager", "min_budget": 80000, "desc": "Branded zip-pouch packaging of Unjha APMC spices for local weekly haats and shops."}
        ]
    },
    "retail": {
        "keywords": ["kirana", "retail", "grocery", "general store", "fertilizer shop", "seeds", "hardware", "shop", "store"],
        "min_capital": 60000,
        "recommended_capital": 250000,
        "industry_name": "Rural Retail & Kirana Provision Store",
        "alternatives": [
            {"name": "Mobile Agrochemical & Farm Input Delivery", "min_budget": 40000, "desc": "On-demand delivery of bio-pesticides and micronutrients directly to farmers' fields."},
            {"name": "Weekly Haat Wholesale Provision Stall", "min_budget": 30000, "desc": "Low-overhead weekly bazaar stall covering APMC market days in nearby talukas."}
        ]
    },
    "engineering": {
        "keywords": ["engineering", "machinery", "fabrication", "lathe", "welding", "metal", "tools", "workshop"],
        "min_capital": 300000,
        "recommended_capital": 750000,
        "industry_name": "Agri-Implements Fabrication & Welding Workshop",
        "alternatives": [
            {"name": "Agricultural Machinery Repair & Maintenance Unit", "min_budget": 75000, "desc": "Tractor, rotavator, and drip irrigation pump servicing workshop."},
            {"name": "Gates, Grills & Farm Fencing Fabrication", "min_budget": 120000, "desc": "Custom welding fabrication for rural construction and farm fencing."}
        ]
    }
}


def extract_taluka(user_text: str):
    """Extract known Mehsana taluka from user input string."""
    if not user_text:
        return None
    text_l = user_text.lower()
    for t in MEHSANA_TALUKAS:
        if t.lower() in text_l:
            return t
        if t.lower() == "mahesana" and "mehsana" in text_l:
            return "Mahesana"
    return None


def extract_business_type(user_text: str):
    """Simple keyword extraction from free text. Returns the matched category key."""
    if not user_text:
        return None
    text_l = user_text.lower()
    
    # Check specialized industry keywords first (e.g. dairy processing vs dairy)
    for category in ["dairy_processing", "food_processing", "textile", "engineering", "dairy", "retail"]:
        if category in INDUSTRY_CAPITAL_BENCHMARKS:
            if any(kw in text_l for kw in INDUSTRY_CAPITAL_BENCHMARKS[category]["keywords"]):
                return category

    for category in CATEGORY_KEYWORDS:
        if category in text_l:
            return category
    for category, kws in CATEGORY_KEYWORDS.items():
        if any(kw in text_l for kw in kws):
            return category
    return None


def extract_investment(user_text: str):
    """
    Extracts budget/investment amount from user text.
    Returns dict: {"raw": str, "amount_inr": int, "formatted": str} or None.
    """
    if not user_text:
        return None
    
    text = user_text.lower()
    
    # 1. Crore matches (e.g. 1.5 crore, 2 cr, 1crore)
    cr_match = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)\b', text, re.IGNORECASE)
    if cr_match:
        val = float(cr_match.group(1))
        inr = int(val * 10000000)
        return {
            "raw": cr_match.group(0).strip(),
            "amount_inr": inr,
            "formatted": f"₹{val:g} Crore{'s' if val > 1 else ''}"
        }
    
    # 2. Lakh matches (e.g. 5 lakh, 2.5 lakhs, 10 lac, 5l, 3.5lakhs)
    lakh_match = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b', text, re.IGNORECASE)
    if lakh_match:
        val = float(lakh_match.group(1))
        inr = int(val * 100000)
        return {
            "raw": lakh_match.group(0).strip(),
            "amount_inr": inr,
            "formatted": f"₹{val:g} Lakh{'s' if val > 1 else ''}"
        }
    
    # 3. K / Thousand matches (e.g. 50k, 80 thousand)
    k_match = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:k|thousand|thousands)\b', text, re.IGNORECASE)
    if k_match:
        val = float(k_match.group(1))
        inr = int(val * 1000)
        return {
            "raw": k_match.group(0).strip(),
            "amount_inr": inr,
            "formatted": f"₹{inr:,}"
        }
    
    # 4. Explicit Currency symbols or Budget keywords followed by numbers (e.g. ₹50000, Rs 75,000, budget 200000)
    num_match = re.search(r'(?:(?:₹|rs\.?|inr|budget|investment)\s*[:=]?\s*)(\d[\d,]{3,})', text, re.IGNORECASE)
    if num_match:
        digits_str = num_match.group(1).replace(",", "")
        inr = int(digits_str)
        if inr >= 10000:
            if inr >= 10000000:
                fmt = f"₹{inr / 10000000:.2g} Crores"
            elif inr >= 100000:
                fmt = f"₹{inr / 100000:.2g} Lakhs"
            else:
                fmt = f"₹{inr:,}"
            return {
                "raw": num_match.group(0).strip(),
                "amount_inr": inr,
                "formatted": fmt
            }

    # 5. Number followed by budget/investment keyword (e.g. '50000 budget')
    num_after_match = re.search(r'(\d[\d,]{3,})\s*(?:budget|investment|capital)', text, re.IGNORECASE)
    if num_after_match:
        digits_str = num_after_match.group(1).replace(',', '')
        inr = int(digits_str)
        if inr >= 10000:
            inr_fmt = f'₹{inr / 100000:.3g} Lakhs' if inr >= 100000 else f'₹{inr:,}'
            return {'raw': num_after_match.group(0).strip(), 'amount_inr': inr, 'formatted': inr_fmt}

    # 6. Number after context prepositions (e.g. 'with 50000', 'for 200000')
    ctx_match = re.search(r'(?:with|of|for|having|at)\s+(\d[\d,]{4,})', text, re.IGNORECASE)
    if ctx_match:
        digits_str = ctx_match.group(1).replace(',', '')
        inr = int(digits_str)
        if inr >= 10000:
            inr_fmt = f'₹{inr / 100000:.3g} Lakhs' if inr >= 100000 else f'₹{inr:,}'
            return {'raw': ctx_match.group(0).strip(), 'amount_inr': inr, 'formatted': inr_fmt}

    return None


def get_fallback_competitors(business_type, taluka):
    """Try Geoapify live search if local MSME data returns nothing."""
    try:
        live_results = fetch_live_competitors_from_geoapify(business_type, taluka)
        if live_results:
            return [
                f"{c['enterprise_name']} (Address: {c['address']})"
                for c in live_results
            ]
    except Exception:
        pass
    return ["(No live map results found for this specific niche category)"]


def get_crop_context(taluka):
    """Pull crops grown in this taluka from the graph."""
    if G is None:
        return []
    tid = f"taluka::{taluka.lower()}"
    if tid not in G:
        return []
    villages = [u for u, v, d in G.in_edges(tid, data=True) if d.get("relation") == "LOCATED_IN"
                and G.nodes[u].get("type") == "Village"]
    crops = set()
    for v in villages[:50]:
        for _, c, d in G.out_edges(v, data=True):
            if d.get("relation") == "GROWS":
                crops.add(G.nodes[c]["name"])
    return sorted(crops)


def evaluate_budget_feasibility(business_type: str, taluka: str, investment_info: dict) -> dict:
    """
    Evaluates whether the user's budget is sufficient for the industry.
    If underfunded, generates alternative local business options and subsidy calculations.
    """
    if not investment_info or "amount_inr" not in investment_info:
        return {}

    user_amount = investment_info["amount_inr"]
    formatted_budget = investment_info["formatted"]
    
    # Match benchmark category
    matched_benchmark = None
    b_key = business_type.lower() if business_type else "retail"
    
    for key, data in INDUSTRY_CAPITAL_BENCHMARKS.items():
        if key in b_key or any(kw in b_key for kw in data["keywords"]):
            matched_benchmark = data
            break
            
    if not matched_benchmark:
        matched_benchmark = INDUSTRY_CAPITAL_BENCHMARKS["retail"]

    min_cap = matched_benchmark["min_capital"]
    rec_cap = matched_benchmark["recommended_capital"]
    ind_name = matched_benchmark["industry_name"]
    
    # Calculate PMEGP Subsidy (35% for rural areas in Gujarat)
    pmegp_subsidy_amount = int(min(user_amount, 5000000) * 0.35)
    bank_loan_eligibility = int(user_amount * 0.90)  # Up to 90% bank loan under PMEGP/Mudra
    
    if user_amount < min_cap:
        feasibility_status = "insufficient"
        shortfall = min_cap - user_amount
        status_text = f"Your budget of {formatted_budget} is lower than the typical setup capital for {ind_name} (starts at ₹{min_cap:,})."
        
        # Filter viable alternatives fitting user's budget
        suitable_alts = [
            alt for alt in matched_benchmark["alternatives"]
            if alt["min_budget"] <= user_amount * 1.3
        ]
        if not suitable_alts:
            suitable_alts = matched_benchmark["alternatives"]
            
    elif user_amount < rec_cap:
        feasibility_status = "moderate"
        shortfall = 0
        status_text = f"Your budget of {formatted_budget} is sufficient to launch a lean/micro unit of {ind_name}."
        suitable_alts = []
    else:
        feasibility_status = "optimal"
        shortfall = 0
        status_text = f"Your budget of {formatted_budget} is optimal for launching a full-scale commercial {ind_name}."
        suitable_alts = []

    return {
        "status": feasibility_status,
        "industry_name": ind_name,
        "user_budget_inr": user_amount,
        "formatted_budget": formatted_budget,
        "min_capital_inr": min_cap,
        "recommended_capital_inr": rec_cap,
        "shortfall_inr": shortfall,
        "status_text": status_text,
        "pmegp_subsidy_amount": pmegp_subsidy_amount,
        "bank_loan_eligibility": bank_loan_eligibility,
        "alternatives": suitable_alts
    }


def build_advisory_context(user_text: str, taluka: str = None, investment: str = None):
    """Gather all raw facts (business idea, location, investment) needed for the report."""
    if not taluka:
        taluka = extract_taluka(user_text)

    business_type = extract_business_type(user_text)
    
    # Extract investment
    investment_info = None
    if investment:
        investment_info = extract_investment(investment)
    if not investment_info:
        investment_info = extract_investment(user_text)

    # Clean business idea if no known category
    if not business_type:
        cleaned = re.sub(r"\b(in|at|for|near|of)\s+[A-Za-z]+", "", user_text, flags=re.IGNORECASE).strip()
        if taluka:
            cleaned = re.sub(rf"\b{taluka}\b", "", cleaned, flags=re.IGNORECASE).strip()
        if investment_info:
            cleaned = re.sub(re.escape(investment_info["raw"]), "", cleaned, flags=re.IGNORECASE).strip()
        # Clean extra budget words
        cleaned = re.sub(r"\b(budget|investment|with|lakh|lakhs|crore|rs|inr|\d+)\b", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned and re.sub(r"[^\w\s]", "", cleaned).strip():
            business_type = cleaned
        else:
            business_type = None

    # Determine missing fields in priority sequence
    if not taluka and not business_type and not investment_info:
        return {
            "error": "no_all",
            "available_talukas": MEHSANA_TALUKAS,
            "budget_presets": BUDGET_PRESETS
        }

    if not business_type:
        return {
            "error": "no_business_type",
            "taluka": taluka,
            "investment": investment_info,
            "available_talukas": MEHSANA_TALUKAS,
            "budget_presets": BUDGET_PRESETS
        }

    if not taluka:
        return {
            "error": "no_location",
            "business_type": business_type if business_type else user_text.strip(),
            "investment": investment_info,
            "available_talukas": MEHSANA_TALUKAS,
            "budget_presets": BUDGET_PRESETS
        }

    if not investment_info:
        return {
            "error": "no_investment",
            "business_type": business_type,
            "taluka": taluka,
            "available_talukas": MEHSANA_TALUKAS,
            "budget_presets": BUDGET_PRESETS
        }

    # All 3 components present -> Assemble complete context
    schemes = match_schemes(business_type)
    exact_competitors, related_competitors = shortlist_competitors(business_type, taluka=taluka)
    crops = get_crop_context(taluka)
    feasibility = evaluate_budget_feasibility(business_type, taluka, investment_info)

    # Competitor list
    if len(exact_competitors) > 0:
        competitor_list = [
            f"{c['enterprise_name']} ({c.get('activity_descriptions', '')[:60]})" 
            for c in exact_competitors[:5]
        ]
        competitor_count = len(exact_competitors)
    else:
        competitor_list = get_fallback_competitors(business_type, taluka)
        competitor_count = len(competitor_list) if competitor_list and competitor_list[0] != "(No live map results found for this specific niche category)" else 0

    return {
        "business_type": business_type,
        "taluka": taluka,
        "investment": investment_info,
        "feasibility": feasibility,
        "schemes": schemes,
        "competitor_count": competitor_count,
        "sample_competitors": competitor_list,
        "local_crops": crops,
    }


def generate_template_report(ctx: dict) -> str:
    """Deterministic, local report generation from the assembled context."""
    if "error" in ctx:
        if ctx["error"] == "no_location":
            return f"Please select your target **Taluka** in Mehsana district for your **{ctx.get('business_type')}** venture."
        elif ctx["error"] == "no_business_type":
            return f"Please select your business idea or sector to evaluate local competition in **{ctx.get('taluka')}** taluka."
        elif ctx["error"] == "no_investment":
            return f"What is your planned investment budget for starting your **{ctx.get('business_type')}** business in **{ctx.get('taluka')}**?"
        return "Please provide your business idea, target Taluka in Mehsana, and planned budget."

    bt, taluka = ctx["business_type"], ctx["taluka"]
    inv = ctx.get("investment", {})
    feas = ctx.get("feasibility", {})
    budget_fmt = inv.get("formatted", "Not specified")

    lines = [f"## 📊 Business Advisory: {bt.title()} in {taluka} Taluka\n"]
    lines.append(f"**Target Location:** {taluka} Taluka, Mehsana District | **Planned Budget:** {budget_fmt}\n")

    # 1. Budget Feasibility & Alternatives
    lines.append("### 💰 Investment Feasibility & Capital Analysis")
    if feas.get("status") == "insufficient":
        lines.append(f"- ⚠️ **Capital Status:** **Underfunded for Full-Scale Setup**")
        lines.append(f"- Standard setup for *{feas.get('industry_name')}* typically requires at least **₹{feas.get('min_capital_inr', 0):,}**, creating a financing gap of **₹{feas.get('shortfall_inr', 0):,}** against your **{budget_fmt}** budget.\n")
        
        if feas.get("alternatives"):
            lines.append(f"#### 🔄 Feasible Alternative Rural Ventures in {taluka}:")
            lines.append(f"Based on local agricultural demand and your **{budget_fmt}** capital, consider these high-margin local alternatives:")
            for alt in feas["alternatives"]:
                lines.append(f"- **{alt['name']}** (Starts from ₹{alt['min_budget']:,}): {alt['desc']}")
            lines.append("")
    elif feas.get("status") == "moderate":
        lines.append(f"- ✅ **Capital Status:** **Viable for Lean / Micro Unit**")
        lines.append(f"- Your budget of **{budget_fmt}** is sufficient to launch a compact, lean unit. You can scale operations after 6-12 months of revenue generation.\n")
    else:
        lines.append(f"- 🌟 **Capital Status:** **Optimal & Fully Funded**")
        lines.append(f"- Your **{budget_fmt}** capital provides robust coverage for machinery, initial inventory, working capital, and contingency reserves.\n")

    # 2. Government Schemes & Subsidies (PMEGP + Mudra)
    lines.append("### 🏛️ Government Subsidies & Low-Interest Loan Schemes")
    pmegp_sub = feas.get("pmegp_subsidy_amount", 0)
    bank_loan = feas.get("bank_loan_eligibility", 0)
    
    lines.append(f"You are eligible for government credit-linked subsidies to fund your setup:")
    lines.append(f"1. **PMEGP (Prime Minister Employment Generation Programme):**")
    lines.append(f"   - **Rural Subsidy:** **35% Govt Subsidy** (Approx. **₹{pmegp_sub:,}** direct capital grant for your project).")
    lines.append(f"   - **Bank Financing:** Up to 90-95% term loan (**₹{bank_loan:,}**), requiring only 5-10% own equity contribution.")
    lines.append(f"2. **Pradhan Mantri MUDRA Yojana:**")
    lines.append(f"   - Collateral-free loans up to ₹10 Lakhs (Shishu up to ₹50k, Kishor ₹50k-₹5L, Tarun ₹5L-₹10L) at subsidized commercial rates.")
    lines.append(f"3. **Gujarat Industrial Policy (MSME Incentive):**")
    lines.append(f"   - 5% to 7% annual interest subsidy on term loans for registered MSMEs in Mehsana district.\n")

    # 3. Competition Analysis
    n = ctx["competitor_count"]
    lines.append("### 🏢 Local Market Competition Analysis")
    if n == 0:
        lines.append(f"- **Density:** Low competition (0 direct registered MSME peers in {taluka}).")
        lines.append(f"- Excellent opportunity to capture early market share or address an underserved village demand.\n")
    elif n < 20:
        lines.append(f"- **Density:** Moderate competition ({n} registered businesses in {taluka}).")
        lines.append(f"- Healthy demand with strong scope for differentiation on quality, packaging, or doorstep delivery.\n")
    else:
        lines.append(f"- **Density:** High density ({n} registered enterprises in {taluka}).")
        lines.append(f"- High player concentration. Focus on specialized sub-niches or strategic highway/APMC locations.\n")

    if ctx.get("sample_competitors"):
        lines.append("**Sample Existing Enterprises in this Taluka:**")
        for c in ctx["sample_competitors"]:
            lines.append(f"- {c}")
        lines.append("")

    # 4. Crop Context
    if ctx.get("local_crops"):
        lines.append("### 🌾 Local Agricultural & Supply Chain Context")
        crops_str = ", ".join(ctx["local_crops"][:10])
        lines.append(f"- Primary local crops in **{taluka}**: {crops_str}.")
        lines.append("- Direct farm-gate procurement significantly lowers input raw material transportation overhead.\n")

    # 5. Next Steps
    lines.append("### 🚀 Strategic Action Plan")
    lines.append(f"1. Finalize your project cost breakdown between machinery (60%), working capital (30%), and permits (10%).")
    lines.append(f"2. Register for **Udyam MSME Certificate** (Free online registration).")
    lines.append(f"3. Submit your PMEGP project application at the **District Industries Centre (DIC) Mehsana** to claim your 35% capital subsidy.")

    return "\n".join(lines)


def generate_with_llm(ctx: dict, api_call_fn = None) -> str:
    """Generates advisory report using Google Gemini with hyper-local context."""
    if api_call_fn is None:
        return generate_template_report(ctx)
        
    competitor_list_str = "\n".join([f"  - {c}" for c in ctx.get('sample_competitors', [])])
    if not competitor_list_str:
        competitor_list_str = "  (No specific exact matches found)"

    inv = ctx.get("investment", {})
    feas = ctx.get("feasibility", {})
    budget_fmt = inv.get("formatted", "Not specified")

    prompt = f"""You are a hyper-local business advisory assistant for rural entrepreneurs
in Mehsana district, Gujarat. Write a practical, professional advisory report formatted in clean Markdown.

PROPOSED VENTURE:
- Business type / sector: {ctx.get('business_type')}
- Target Location: {ctx.get('taluka')} taluka, Mehsana District, Gujarat
- User Planned Investment Budget: {budget_fmt} (Amount: ₹{inv.get('amount_inr', 0):,})

CAPITAL ADEQUACY & FEASIBILITY CONTEXT:
- Capital Status: {feas.get('status')}
- Standard Industry Minimum Setup Cost: ₹{feas.get('min_capital_inr', 0):,}
- Recommended Commercial Setup Cost: ₹{feas.get('recommended_capital_inr', 0):,}
- Financing Shortfall (if any): ₹{feas.get('shortfall_inr', 0):,}
- Suitable Lower-Capital Local Alternatives in {ctx.get('taluka')}: {feas.get('alternatives')}

LOCAL MARKET & COMPETITION DATA:
- Total registered MSME competitors in {ctx.get('taluka')}: {ctx.get('competitor_count')}
- Sample local competitor names:
{competitor_list_str}

GOVERNMENT SCHEMES & SUBSIDY METRICS:
- PMEGP 35% Rural Subsidy Amount: Approx. ₹{feas.get('pmegp_subsidy_amount', 0):,}
- Maximum Bank Loan Eligibility: Up to ₹{feas.get('bank_loan_eligibility', 0):,}
- Applicable Schemes Catalog: {ctx.get('schemes')}
- Local Crops / Raw Materials: {ctx.get('local_crops')}

INSTRUCTIONS FOR YOUR RESPONSE:
1. Executive Feasibility Assessment:
   - Explicitly evaluate whether the user's budget ({budget_fmt}) is sufficient for {ctx.get('business_type')} in {ctx.get('taluka')}.
   - If underfunded: Warn gently, explain the shortfall, and prominently feature 2-3 practical, lower-capital alternative rural businesses specifically suited for {ctx.get('taluka')} that can be started within their exact budget.
   - If sufficient: Detail project cost allocation (Machinery, Working capital, Licensing).
2. Government Subsidies & Low-Interest Financing:
   - Provide concrete financial calculations for PMEGP (35% capital subsidy = ₹{feas.get('pmegp_subsidy_amount', 0):,}) and Mudra Loan options.
   - Explain how government subsidies can bridge any capital gaps.
3. Market Competition & Local Saturation in {ctx.get('taluka')}:
   - Mention 3-5 existing registered competitors from the local MSME data.
4. Local Raw Material & Supply Chain Advantages in {ctx.get('taluka')}.
5. Step-by-Step Action Plan for the entrepreneur.
"""

    try:
        return api_call_fn(prompt)
    except Exception as e:
        print(f"LLM generation failed ({e}), falling back to local template report.")
        return generate_template_report(ctx)


def advise_structured(user_text: str, taluka: str = None, investment: str = None, use_llm: bool = True, api_call_fn = None) -> dict:
    """
    Returns structured advisory result or 'needs_info' metadata when input is partial.
    """
    ctx = build_advisory_context(user_text, taluka, investment)
    if "error" in ctx:
        err = ctx["error"]
        if err == "no_location":
            b_name = (ctx.get("business_type") or "Your Business Idea").strip()
            return {
                "status": "needs_info",
                "missing_field": "taluka",
                "business_type": b_name,
                "investment": ctx.get("investment"),
                "available_talukas": MEHSANA_TALUKAS,
                "budget_presets": BUDGET_PRESETS,
                "reply": f"Please select your target **Taluka** in Mehsana district for your **{b_name}** venture:"
            }
        elif err == "no_business_type":
            t_name = ctx.get("taluka", "Mehsana")
            return {
                "status": "needs_info",
                "missing_field": "business_type",
                "taluka": t_name,
                "investment": ctx.get("investment"),
                "available_talukas": MEHSANA_TALUKAS,
                "budget_presets": BUDGET_PRESETS,
                "suggested_categories": [
                    "Dairy & Milk Processing",
                    "Textile & Garments",
                    "Spice Processing & Trading",
                    "Retail & Kirana Store",
                    "Engineering & Machinery"
                ],
                "reply": f"What type of business are you planning to start in **{t_name}** taluka?"
            }
        elif err == "no_investment":
            b_name = ctx.get("business_type", "business")
            t_name = ctx.get("taluka", "Mehsana")
            return {
                "status": "needs_info",
                "missing_field": "investment",
                "business_type": b_name,
                "taluka": t_name,
                "available_talukas": MEHSANA_TALUKAS,
                "budget_presets": BUDGET_PRESETS,
                "reply": f"What is your planned **investment budget** for starting a **{b_name}** venture in **{t_name}** taluka?"
            }
        else:
            return {
                "status": "needs_info",
                "missing_field": "all",
                "available_talukas": MEHSANA_TALUKAS,
                "budget_presets": BUDGET_PRESETS,
                "reply": "Please provide your business idea, target Taluka in Mehsana, and planned budget (e.g. *'Dairy shop in Kadi with ₹5 Lakhs budget'*)."
            }

    if use_llm and api_call_fn:
        report = generate_with_llm(ctx, api_call_fn)
    else:
        report = generate_template_report(ctx)

    return {
        "status": "success",
        "business_type": ctx.get("business_type"),
        "taluka": ctx.get("taluka"),
        "investment": ctx.get("investment"),
        "feasibility": ctx.get("feasibility"),
        "reply": report
    }


def advise(user_text: str, taluka: str = None, investment: str = None, use_llm: bool = True, api_call_fn = None):
    res = advise_structured(user_text, taluka, investment, use_llm, api_call_fn)
    return res.get("reply", "")


if __name__ == "__main__":
    test_q = "Commercial dairy processing plant in Kadi with ₹50,000 budget"
    print(advise(test_q))