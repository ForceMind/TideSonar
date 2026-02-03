import requests

LICENSE = ""

def test_endpoint(name, url):
    print(f"Testing {name}: {url}")
    try:
        resp = requests.get(url, timeout=10)
        print(f"   -> Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"   -> Success! Preview: {resp.text[:100]}")
        else:
            print(f"   -> Failed. Body: {resp.text[:100]}")
    except Exception as e:
        print(f"   -> Error: {e}")
    print("-" * 40)

def run():
    print(f"License: {LICENSE[:8]}******")
    
    # 1. Single Stock Realtime
    test_endpoint("Single Realtime (000001)", f"http://api.biyingapi.com/hsrl/ssjy/000001/{LICENSE}")
    
    # 2. Batch Realtime (Few stocks)
    test_endpoint("Batch Realtime (Small)", f"http://api.biyingapi.com/hsrl/ssjy_more/{LICENSE}?stock_codes=000001,600519")
    
    # 3. All Market Realtime (The one we moved away from)
    test_endpoint("Full Market Snapshot", f"http://api.biyingapi.com/hsrl/real/all/{LICENSE}")

if __name__ == "__main__":
    run()
