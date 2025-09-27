import requests
import os
import json
from dotenv import load_dotenv
from datetime import date, datetime, timedelta
import pandas as pd
load_dotenv()
# ------------------------------
# CONFIGURATION
# ------------------------------
API_TOKEN = os.getenv("API_TOKEN")
ZONE_ID = os.getenv("ZONE_ID")

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

url = "https://api.cloudflare.com/client/v4/graphql"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

url = "https://api.cloudflare.com/client/v4/graphql"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

url = "https://api.cloudflare.com/client/v4/graphql"

end_date = date.today()
start_date = end_date - timedelta(days=1)

query = f"""
{{
  viewer {{
    zones(filter: {{ zoneTag: "{ZONE_ID}" }}) {{
      httpRequests1dGroups(
        limit: 1
        filter: {{ date_geq: "{start_date}", date_leq: "{end_date}" }}
      ) {{
        dimensions {{ date }}
        sum {{
          countryMap {{
            clientCountryName
            requests
            bytes
            threats
          }}
        }}
      }}
    }}
  }}
}}
"""

resp = requests.post(url, headers=headers, json={"query": query})
print(json.dumps(resp.json(), indent=2))