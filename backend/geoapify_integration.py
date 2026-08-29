import os
import requests

def fetch_live_competitors_from_geoapify(business_query, taluka_name, district="Mehsana"):
    """
    Fetches real-time local businesses using the Geoapify Places API.
    Requires a GEOAPIFY_API_KEY environment variable.
    """
    api_key = os.environ.get("GEOAPIFY_API_KEY")
    if not api_key:
        print("Warning: GEOAPIFY_API_KEY not set. Skipping live lookup.")
        return []

    # Geoapify text/places endpoint structure
    url = "https://api.geoapify.com/v2/places"
    
    # Construct a descriptive text query for the area
    search_text = f"{business_query} in {taluka_name}, {district}, Gujarat, India"
    
    params = {
        "text": search_text,
        "limit": 10,
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        competitors = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            competitors.append({
                "enterprise_name": props.get("name") or props.get("address_line1") or "Unknown Enterprise",
                "address": props.get("formatted", "N/A"),
                "category": ", ".join(props.get("categories", ["business"]))
            })
        return competitors
    except Exception as e:
        print(f"Error fetching from Geoapify API: {e}")
        return []

if __name__ == "__main__":
    # Test block
    os.environ["GEOAPIFY_API_KEY"] = "YOUR_ACTUAL_GEOAPIFY_KEY"
    results = fetch_live_competitors_from_geoapify("dairy", "Kheralu")
    for r in results:
        print(f"- {r['enterprise_name']} | {r['address']}")
        