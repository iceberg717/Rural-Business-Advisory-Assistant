"""
Business Advisory Assistant — orchestrates schemes + competitors + market
context into one advisory report, given a business idea + location.

Two modes:
  - TEMPLATE mode (default, works offline, free, no API needed): assembles real
    data from local MSME database, knowledge graph, and scheme records into a structured, readable report.
  - LLM mode (Google Gemini): sends the assembled hyper-local context to Gemini
    with automatic fallback to Template mode if API keys or network are unavailable.
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

def extract_taluka(user_text: str):
    """Extract known Mehsana taluka from user input string."""
    if not user_text:
        return None
    text_l = user_text.lower()
    for t in MEHSANA_TALUKAS:
        # Match 'mehsana' or 'mahesana'
        if t.lower() in text_l:
            return t
        if t.lower() == "mahesana" and "mehsana" in text_l:
            return "Mahesana"
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


def extract_business_type(user_text):
    """Simple keyword extraction from free text. Returns the matched category key."""
    text_l = user_text.lower()
    for category in CATEGORY_KEYWORDS:
        if category in text_l:
            return category
    # try matching individual keywords too (e.g. "milk" -> dairy)
    for category, kws in CATEGORY_KEYWORDS.items():
        if any(kw in text_l for kw in kws):
            return category
    return None


def get_crop_context(taluka):
    """Pull crops grown in this taluka from the graph, in case it's relevant
    (e.g. dairy/food-processing businesses benefit from knowing local crop supply)."""
    if G is None:
        return []
    tid = f"taluka::{taluka.lower()}"
    if tid not in G:
        return []
    villages = [u for u, v, d in G.in_edges(tid, data=True) if d.get("relation") == "LOCATED_IN"
                and G.nodes[u].get("type") == "Village"]
    crops = set()
    for v in villages[:50]:  # cap for speed
        for _, c, d in G.out_edges(v, data=True):
            if d.get("relation") == "GROWS":
                crops.add(G.nodes[c]["name"])
    return sorted(crops)


def build_advisory_context(user_text, taluka=None):
    """Gather all the raw facts needed for the report."""
    if not taluka:
        taluka = extract_taluka(user_text)

    business_type = extract_business_type(user_text)
    
    # If we can't extract a known category, clean the user input as business idea
    if not business_type:
        cleaned = re.sub(r"\b(in|at|for|near|of)\s+[A-Za-z]+", "", user_text, flags=re.IGNORECASE).strip()
        business_type = cleaned if cleaned else user_text.strip()
        
    if not taluka:
        return {
            "error": "no_location",
            "business_type": business_type,
            "available_talukas": MEHSANA_TALUKAS
        }

    schemes = match_schemes(business_type)
    exact_competitors, related_competitors = shortlist_competitors(business_type, taluka=taluka)
    crops = get_crop_context(taluka)

    # --- GEOAPIFY FALLBACK LOGIC ---
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
        "schemes": schemes,
        "competitor_count": competitor_count,
        "sample_competitors": competitor_list,
        "local_crops": crops,
    }


def generate_template_report(ctx):
    """Deterministic, local report generation from the assembled context."""
    if "error" in ctx:
        if ctx["error"] == "no_location":
            taluka_list_str = ", ".join(MEHSANA_TALUKAS)
            return (
                f"### Business Idea: **{ctx['business_type'].title()}**\n\n"
                f"To provide you with local competitor intelligence and applicable government schemes, "
                f"please specify your target **Taluka** in Mehsana district.\n\n"
                f"📍 **Available Talukas:** {taluka_list_str}\n\n"
                f"*Example:* `I want to start a {ctx['business_type']} business in Kadi`"
            )
        return ctx["error"]

    bt, taluka = ctx["business_type"], ctx["taluka"]
    lines = [f"## 📊 Business Advisory: {bt.title()} in {taluka} Taluka\n"]

    # competition
    n = ctx["competitor_count"]
    if n == 0:
        lines.append(f"### 🏢 Market Competition Analysis\n"
                     f"- **Status:** Low competition detected.\n"
                     f"- No registered {bt} MSMEs currently recorded in **{taluka}** taluka. This indicates an open market opportunity or an underserved niche worth validating with local foot traffic.\n")
    elif n < 20:
        lines.append(f"### 🏢 Market Competition Analysis\n"
                     f"- **Status:** Moderate Competition ({n} registered businesses in {taluka}).\n"
                     f"- There is healthy market demand with room for differentiation on pricing, product quality, or strategic sub-village location.\n")
    else:
        lines.append(f"### 🏢 Market Competition Analysis\n"
                     f"- **Status:** High Competition / Saturated ({n} registered businesses in {taluka}).\n"
                     f"- High density of existing players. We recommend focusing on value-added services, unique supply chains, or targeting adjacent underserved villages.\n")

    if ctx.get("sample_competitors"):
        lines.append("**Sample Existing Enterprises in this Taluka:**")
        for c in ctx["sample_competitors"]:
            lines.append(f"- {c}")
        lines.append("")

    # schemes
    lines.append("### 🏛️ Government Schemes & Financial Support")
    if ctx["schemes"]:
        lines.append(f"Found **{len(ctx['schemes'])} applicable government schemes** for your business profile:\n")
        for s in ctx["schemes"]:
            verified = "✅ Verified" if "Verified" in s.get("verification", "") else "ℹ️ Available"
            lines.append(f"- **{s['name']}** ({s.get('scheme_id', 'Govt Scheme')}):")
            lines.append(f"  - **Max Loan:** {s.get('max_loan', 'As per guideline')}")
            lines.append(f"  - **Interest Rate:** {s.get('interest_rate', 'Subsidized')}")
            lines.append(f"  - **Subsidy:** {s.get('subsidy', 'Applicable')} ({verified})")
            if s.get("target_group"):
                lines.append(f"  - **Target Group:** {s.get('target_group')}")
        lines.append("")
    else:
        lines.append("- No category-specific scheme directly mapped in our primary catalog. "
                     "However, standard MSME / PMEGP and Mudra loans apply universally through the District Industries Centre (DIC) Mehsana.\n")

    # crop context (only if relevant)
    if ctx.get("local_crops"):
        lines.append("### 🌾 Local Agricultural & Raw Material Context")
        crops_str = ", ".join(ctx["local_crops"][:10])
        lines.append(f"- Key local crops in **{taluka}**: {crops_str}.")
        lines.append("- Potential advantage: direct farm-gate raw material sourcing reduces transport overhead.\n")

    lines.append("### 💡 Recommended Next Steps")
    lines.append("1. Validate local customer footfall in the commercial market of your chosen village/taluka.")
    lines.append("2. Apply for Udyam Registration (free online MSME certification).")
    lines.append("3. Approach your local nationalized bank or DIC office with your project report to apply for the listed subsidy scheme.")

    return "\n".join(lines)


def generate_with_llm(ctx, api_call_fn=None):
    if api_call_fn is None:
        return generate_template_report(ctx)
        
    competitor_list_str = "\n".join([f"  - {c}" for c in ctx.get('sample_competitors', [])])
    if not competitor_list_str:
        competitor_list_str = "  (No specific exact matches found)"

    prompt = f"""You are a hyper-local business advisory assistant for rural entrepreneurs
in Mehsana district, Gujarat. Write a practical, professional advisory report formatted in clean Markdown.

Business type: {ctx.get('business_type')}
Location: {ctx.get('taluka')} taluka, Mehsana District
Total registered competitors in this taluka: {ctx.get('competitor_count')}
List of actual local competitors from MSME database:
{competitor_list_str}

Applicable government schemes & loans: {ctx.get('schemes')}
Locally grown crops/raw materials: {ctx.get('local_crops')}

Provide a structured, encouraging, and highly specific advisory response:
1. Executive Summary & Market Saturation Assessment in {ctx.get('taluka')}.
2. Local Competition Snapshot (mentioning 3-5 existing registered business names).
3. Recommended Government Scheme with Loan Amount & Subsidy details.
4. Strategic Differentiation & Actionable Next Steps."""

    try:
        return api_call_fn(prompt)
    except Exception as e:
        print(f"LLM generation failed ({e}), falling back to local template report.")
        return generate_template_report(ctx)


def advise(user_text: str, taluka: str = None, use_llm: bool = True, api_call_fn = None):
    ctx = build_advisory_context(user_text, taluka)
    if "error" in ctx:
        return generate_template_report(ctx)

    if use_llm and api_call_fn:
        return generate_with_llm(ctx, api_call_fn)
        
    return generate_template_report(ctx)


if __name__ == "__main__":
    print(advise("give me idea for my textile business in Visnagar"))