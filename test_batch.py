import requests
import json
from backend.app.core.config import settings

license = settings.BIYING_LICENSE
url = f"http://api.biyingapi.com/hsrl/ssjy_more/{license}"
# Try a few known codes
params = {"stock_codes": "000001,000002,600000"}
print(f"Testing Batch: {url} with {params}")

try:
    resp = requests.get(url, params=params, timeout=10)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Type: {type(data)}")
        if isinstance(data, list):
            print(f"Count: {len(data)}")
            if len(data) > 0:
                print("First Item Type:", type(data[0]))
                print("First Item:", data[0])
        else:
            print("Not a list")
except Exception as e:
    print(f"Error: {e}")
