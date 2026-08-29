import csv

TALUKA_KEYWORDS = ["KHERALU", "VADNAGAR", "BECHARAJI", "SATLASANA", "VISNAGAR",
                    "UNJHA", "VIJAPUR", "KADI", "MEHSANA", "MAHESANA"]
# normalize MEHSANA/MAHESANA to one taluka name
CANON = {"MEHSANA": "Mahesana", "MAHESANA": "Mahesana", "KHERALU": "Kheralu",
         "VADNAGAR": "Vadnagar", "BECHARAJI": "Becharaji", "SATLASANA": "Satlasana",
         "VISNAGAR": "Visnagar", "UNJHA": "Unjha", "VIJAPUR": "Vijapur", "KADI": "Kadi"}

with open("msme_clean.csv") as f:
    rows = list(csv.DictReader(f))

matched = 0
for r in rows:
    addr = r["address"].upper()
    taluka = ""
    for kw in TALUKA_KEYWORDS:
        if kw in addr:
            taluka = CANON[kw]
            matched += 1
            break
    r["taluka"] = taluka

with open("msme_clean.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"Tagged {matched}/{len(rows)} MSME rows with taluka (extracted from address text)")
