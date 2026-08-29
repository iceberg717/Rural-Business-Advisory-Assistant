"""
Business Advisory Assistant — orchestrates schemes + competitors + market
context into one advisory report, given a business idea + location.

Two modes:
  - TEMPLATE mode (default, works now, free, no API needed): assembles real
    data into a structured, readable report using Python string templates.
  - LLM mode (stub — wire in your own API key when deploying for real):
    same assembled context, but sent to an LLM for a more natural,
    conversational write-up. See generate_with_llm() below for the swap-in point.
"""
from match_schemes import match_schemes
from shortlist_competitors import shortlist_competitors, CATEGORY_KEYWORDS
from geoapify_integration import fetch_live_competitors_from_geoapify

import pickle
with open("mehsana_graph.pkl", "rb") as f:
    G = pickle.load(f)


def get_fallback_competitors(business_type, taluka):
    """Try Geoapify live search if local MSME data returns nothing."""
    live_results = fetch_live_competitors_from_geoapify(business_type, taluka)
    
    if live_results:
        return [
            f"{c['enterprise_name']} (Address: {c['address']})"
            for c in live_results
        ]
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
    """Gather all the raw facts needed for the report. This is what you'd
    hand to an LLM if using LLM mode, or feed to the template below."""
    business_type = extract_business_type(user_text)
    
    # FIX: If we can't extract a known category, use the exact words the user typed
    if not business_type:
        business_type = user_text.strip()
        
    if not taluka:
        return {"error": "no_location", "business_type": business_type}

    schemes = match_schemes(business_type)
    exact_competitors, related_competitors = shortlist_competitors(business_type, taluka=taluka)
    crops = get_crop_context(taluka)

    # --- GEOAPIFY FALLBACK LOGIC ---
    if len(exact_competitors) > 0:
        competitor_list = [
            f"{c['enterprise_name']} ({c['activity_descriptions'][:60]})" 
            for c in exact_competitors[:5]
        ]
        competitor_count = len(exact_competitors)
    else:
        # Zero local records found -> Switch to Geoapify Live Maps search!
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
    """Deterministic, no-LLM report generation from the assembled context."""
    if "error" in ctx:
        if ctx["error"] == "no_location":
            return (f"I identified this as a **{ctx['business_type']}** business idea, "
                     f"but I need to know which taluka you're planning it in (e.g. Kadi, "
                     f"Unjha, Visnagar, Kheralu...) to check local competition and applicable schemes.")
        return ctx["error"]

    bt, taluka = ctx["business_type"], ctx["taluka"]
    lines = [f"## Business Advisory: {bt.title()} business in {taluka} taluka\n"]

    # competition
    n = ctx["competitor_count"]
    if n == 0:
        lines.append(f"**Competition:** No existing {bt} businesses found in {taluka} in our registered "
                      f"MSME data — this could mean low competition, or an underserved area worth validating further.\n")
    elif n < 20:
        lines.append(f"**Competition:** {n} existing {bt} businesses registered in {taluka} — "
                      f"moderate competition. Worth differentiating on location, product range, or price.\n")
    else:
        lines.append(f"**Competition:** {n} existing {bt} businesses already registered in {taluka} — "
                      f"this market looks saturated. Consider a niche angle or a different taluka.\n")
    if ctx["sample_competitors"]:
        lines.append("Sample existing competitors:")
        for c in ctx["sample_competitors"]:
            lines.append(f"  - {c}")
        lines.append("")

    # schemes
    if ctx["schemes"]:
        lines.append(f"**Applicable government schemes ({len(ctx['schemes'])} found):**")
        for s in ctx["schemes"]:
            verified = "✓" if "Verified" in s.get("verification", "") else "⚠ needs verification"
            lines.append(f"  - {s['name']}: max loan {s['max_loan']}, interest {s['interest_rate']}, "
                          f"subsidy {s['subsidy']} [{verified}]")
        lines.append("")
    else:
        lines.append("**Applicable government schemes:** none of the 7 tracked schemes matched this "
                      "category directly — worth checking district DIC office for other options.\n")

    # crop context (only if relevant)
    if ctx["local_crops"] and bt in ("dairy", "food processing", "agri-business"):
        lines.append(f"**Local raw material context:** {taluka} villages grow: "
                      f"{', '.join(ctx['local_crops'][:8])} — relevant for sourcing if applicable.\n")

    return "\n".join(lines)


def generate_with_llm(ctx, api_call_fn=None):
    if api_call_fn is None:
        from advisory_assistant import generate_template_report
        return generate_template_report(ctx)
        
    # Format the sample competitors clearly for the LLM
    competitor_list_str = "\n".join([f"  - {c}" for c in ctx.get('sample_competitors', [])])
    if not competitor_list_str:
        competitor_list_str = "  (No specific exact matches found)"

    prompt = f"""You are a hyper-local business advisory assistant for rural entrepreneurs
in Mehsana district, Gujarat. Write a practical, professional advisory report.

Business type: {ctx.get('business_type')}
Location: {ctx.get('taluka')} taluka
Total registered competitors in this taluka: {ctx.get('competitor_count')}
List of actual local competitors from MSME database or live maps:
{competitor_list_str}

Applicable government schemes & loans: {ctx.get('schemes')}
Locally grown crops/raw materials: {ctx.get('local_crops')}

In your response, you MUST explicitly:
1. State the exact number of local competitors in {ctx.get('taluka')} taluka.
2. List out at least 3-5 specific competitor enterprise names and their activities/addresses from the provided list above so the user knows who is operating nearby.
3. Give an honest read on market saturation.
4. Recommend the best-fit government scheme with loan and subsidy numbers.
5. Provide a concrete differentiation strategy."""

    return api_call_fn(prompt)


def advise(user_text, taluka=None, use_llm=False, api_call_fn=None):
    ctx = build_advisory_context(user_text, taluka)
    if use_llm:
        return generate_with_llm(ctx, api_call_fn)
    return generate_template_report(ctx)


if __name__ == "__main__":
    print(advise("give me idea for my textile business"))
    print("\n" + "=" * 70 + "\n")
    print(advise("give me idea for my textile business", taluka="Visnagar"))
    print("\n" + "=" * 70 + "\n")
    print(advise("thinking of starting a dairy shop", taluka="Kheralu"))