import requests

LICENSE = "7E1A1BA6-0402-4505-82B1-ECCAA7281B26"

def test_code(code_str):
    url = f"http://api.biyingapi.com/hsrl/ssjy_more/{LICENSE}"
    print(f"Testing codes: '{code_str}'")
    try:
        resp = requests.get(url, params={"stock_codes": code_str})
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Success. Count: {len(resp.json())}")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Ex: {e}")

if __name__ == "__main__":
    test_code("000001,600519")       # Pure
    test_code("000001.SZ,600519.SH") # With Suffix
