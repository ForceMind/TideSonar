import requests
import time

LICENSE = ""
URL = f"http://api.biyingapi.com/hsrl/ssjy_more/{LICENSE}"

def test_batch():
    # Test a small batch of known good stocks
    codes = "600000,000001,600519"
    print(f"Testing Batch API: {URL}")
    print(f"Codes: {codes}")
    
    try:
        resp = requests.get(URL, params={"stock_codes": codes}, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {resp.headers}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Data Sample: {str(data)[:200]}")
        else:
            print(f"Error Body: {resp.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_batch()
