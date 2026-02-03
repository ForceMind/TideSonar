import requests
import json
from backend.app.core.config import settings

license = settings.BIYING_LICENSE
# Note: domain is different in doc: all.biyingapi.com
url = f"http://all.biyingapi.com/hsrl/real/all/{license}"
print(f"Testing Full Snapshot: {url}")

try:
    resp = requests.get(url, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Type: {type(data)}")
        if isinstance(data, list):
            print(f"Count: {len(data)}")
            if len(data) > 0:
                print("First Item:", data[0])
            else:
                print("Empty List")
        else:
            print("Not a list")
    else:
        print("Failed")
except Exception as e:
    print(f"Error: {e}")
