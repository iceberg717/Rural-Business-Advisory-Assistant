import os
import csv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MSME_CSV_PATH = os.path.join(CURRENT_DIR, "msme_clean.csv")

def fetch_msme_competitors(business_category, taluka_name, max_results=10):
    """
    Queries msme_clean.csv directly to retrieve exact local competitors
    matched by taluka and business category keywords.
    """
    # Define search keywords mapping
    category_keywords = {
        "dairy": ["dairy", "milk", "ghee", "paneer", "curd", "butter", "khoya", "pashupalan"],
        "retail": ["retail", "grocery", "general store", "kirana", "shop", "parlour", "super market"],
        "food processing": ["food processing", "spice", "masala", "flour mill", "oil mill", "pickle", "snack", "bakery"],
        "textile": ["textile", "weaving", "garment", "tailoring", "yarn", "cotton", "cloth"],
        "computer/it": ["computer", "software", "it services", "consultancy"],
        "agri-business": ["seed", "fertilizer", "agri", "farming", "pesticide", "mandi"]
    }
    
    keywords = category_keywords.get(business_category.lower(), [business_category.lower()])
    
    matches = []
    if not os.path.exists(MSME_CSV_PATH):
        return []
    with open(MSME_CSV_PATH, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check taluka match (case-insensitive)
            row_taluka = row.get("taluka", "").strip().lower()
            if row_taluka != taluka_name.strip().lower():
                continue
                
            # Check description keyword match
            desc = row.get("activity_descriptions", "").lower()
            if any(kw in desc for kw in keywords):
                matches.append(row)
                
    return matches[:max_results]

if __name__ == "__main__":
    # Example test query: Retail competitors in Unjha
    taluka = "Unjha"
    category = "retail"
    
    competitors = fetch_msme_competitors(category, taluka, max_results=10)
    
    print(f"\n=== MSME Registry Competitor Query ===")
    print(f"Target: {category.upper()} businesses in {taluka} Taluka")
    print(f"Found {len(competitors)} sample enterprises:\n")
    
    for idx, comp in enumerate(competitors, 1):
        name = comp.get("enterprise_name", "Unknown")
        address = comp.get("address", "N/A")
        activity = comp.get("activity_descriptions", "N/A")
        print(f"{idx}. {name}")
        print(f"   Address: {address}")
        print(f"   Activity: {activity}\n")