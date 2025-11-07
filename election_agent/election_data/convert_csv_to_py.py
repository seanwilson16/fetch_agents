import pandas as pd
import math

df = pd.read_csv(
    "1976-2020-president.csv",
    usecols=["year", "state", "candidate", "party_detailed", "candidatevotes", "totalvotes"]
)

records = df.to_dict(orient="records")

with open("election_data.py", "w", encoding="utf-8") as f:
    f.write("# Auto-generated from 1976-2020-president.csv\n")
    f.write("data = [\n")
    for rec in records:
        # Handle missing candidate
        candidate = rec["candidate"]
        if isinstance(candidate, float) and math.isnan(candidate):
            rec["candidate"] = "UNKNOWN CANDIDATE"

        # Handle missing party
        party = rec["party_detailed"]
        if isinstance(party, float) and math.isnan(party):
            rec["party_detailed"] = "OTHER"

        # Handle missing vote numbers
        for key in ["candidatevotes", "totalvotes"]:
            if isinstance(rec[key], float) and math.isnan(rec[key]):
                rec[key] = None

        f.write(f"    {rec},\n")
    f.write("]\n")
