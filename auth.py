import requests
import os
from dotenv import load_dotenv
load_dotenv()
# ------------------------------
# CONFIGURATION
# ------------------------------
API_TOKEN = os.getenv("API_TOKEN")
print(API_TOKEN)
ACCOUNT_ID = os.getenv("ACCOUNT_ID")  # same one from your curl

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/tokens/verify"
resp = requests.get(url, headers=headers)
print(resp.json())