import requests
import json
import os

key = "F24C64AA-5042-4A7A-AAEE-F9425AED8B81" # Using the one user just entered for test
url = f"http://api.biyingapi.com/hszg/zg/000009/{key}"

print(f"Checking 000009 (Likely ZZ500): {url}")
try:
    resp = requests.get(url, timeout=10)
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(e)
