import requests
import sys
import json

def test_api(license_key):
    print(f"\n[Test] Connecting to Biying API with key: {license_key[:6]}******")
    
    # ---------------------------------------------------------
    # 1. 探索“指数、行业、概念树”接口 (hszg/list)
    #    这是最可能找到 "中证500", "中证1000" 正确代码的地方
    # ---------------------------------------------------------
    tree_url = f"http://api.biyingapi.com/hszg/list/{license_key}"
    print(f"\n[Task 1] Scanning Index Tree: {tree_url}")
    
    target_names = ["沪深300", "中证500", "中证1000", "中证2000", "国证2000", "上证指数", "深证成指"]
    found_map = {}

    try:
        resp = requests.get(tree_url, timeout=20)
        if resp.status_code == 200:
            tree_data = resp.json()
            print(f"✅ Tree Data Fetched. Total Nodes: {len(tree_data)}")
            
            for item in tree_data:
                name = item.get('name', '')
                code = item.get('code', '')
                
                # Check against targets
                for t in target_names:
                    if t in name:
                        # 记录找到的匹配项。我们倾向于找到精确的，但先收集所有。
                        # 格式: { "中证500": ["zz500", "000905"], ... }
                        if t not in found_map:
                            found_map[t] = []
                        found_map[t].append({"name": name, "code": code})
                        print(f"   -> Match Found: {name} (Code: {code})")
        else:
            print(f"❌ Failed to fetch tree: {resp.status_code}")
    except Exception as e:
        print(f"❌ Error fetching tree: {e}")

    # ---------------------------------------------------------
    # 2. 探索“一级市场板块” (hslt/primarylist) - 深度搜索
    # ---------------------------------------------------------
    prim_url = f"http://api.biyingapi.com/hslt/primarylist/{license_key}"
    print(f"\n[Task 2] Deep Dive into Primary Sectors: {prim_url}")
    
    sector_candidates = []
    
    try:
        resp = requests.get(prim_url, timeout=15)
        if resp.status_code == 200:
            prim_data = resp.json()
            print(f"✅ Primary List Fetched. Count: {len(prim_data)}")
            
            # Search for 1000/2000 related sectors
            keywords = ["1000", "2000", "中证"]
            
            print(f"   Scanning for keywords: {keywords}...")
            for item in prim_data:
                # API Doc says field is 'mc' (name) or sometimes just value in list?
                # User sample output was ['000809', '1000价值'] so it seems it's a list of strings OR dicts?
                # Let's handle both.
                name = ""
                if isinstance(item, dict):
                    name = item.get('mc', '')
                elif isinstance(item, str):
                    name = item
                    
                for kw in keywords:
                    if kw in name:
                        print(f"   -> Found Sector Candidate: {name}")
                        sector_candidates.append(name)
                        break 
        else:
            print(f"⚠️  Primary List returned {resp.status_code}")
    except Exception as e:
        print(f"❌ Error fetching primary list: {e}")

    # ---------------------------------------------------------
    # 2.1 验证板块成分 (Sector Constituents)
    # ---------------------------------------------------------
    if sector_candidates:
        print(f"\n[Task 2.1] Fetching details for candidate sectors...")
        for sec_name in sector_candidates:
            # Skip if it doesn't look like what we want (heuristic)
            if "期货" in sec_name: continue
            
            # URL: http://api.biyingapi.com/hslt/sectors/NAME/LICENSE
            sec_url = f"http://api.biyingapi.com/hslt/sectors/{sec_name}/{license_key}"
            print(f"   Fetching sector '{sec_name}' ...", end="")
            
            try:
                # Ensure the section name is URL encoded properly if requests doesn't do it automatically enough for this specific API style
                # But requests usually handles it. Let's try raw first.
                r = requests.get(sec_url, timeout=10)
                if r.status_code == 200:
                    stocks = r.json()
                    if isinstance(stocks, list):
                        count = len(stocks)
                        print(f" ✅ Got {count} stocks")
                        if count > 800 and "1000" in sec_name:
                            print(f"      !!! POTENTIAL CSI 1000 MATCH !!!")
                        if count > 1500 and "2000" in sec_name:
                            print(f"      !!! POTENTIAL CSI 2000 MATCH !!!")
                    else:
                        print(f" ❌ Invalid format. Type: {type(stocks)}")
                        print(f"      Response preview: {str(stocks)[:200]}")
                else:
                    print(f" ❌ HTTP {r.status_code}")
                    print(f"      Response: {r.text[:200]}")
            except Exception as e:
                print(f" ❌ Error: {e}")
    else:
        print("   No sector candidates found to test.")

    # ---------------------------------------------------------
    # 3. 验证发现的代码是否可用 (Constituents Check)
    # ---------------------------------------------------------
    print(f"\n[Task 3] Verifying constituents for found codes...")
    
    # Prioritize codes to test
    codes_to_test = []
    
    # Helper to pick best code
    for t in target_names:
        matches = found_map.get(t, [])
        if matches:
            # 简单策略：取第一个。通常 tree 接口返回的比较靠谱
            # 如果有多个，优先选 纯字母 或 纯数字? Biying 似乎用字母如 hs300
            best_match = matches[0]['code']
            codes_to_test.append((t, best_match))
    
    if not codes_to_test:
        print("⚠️  No index codes found in Tree. Cannot verify constituents.")
    
    for name, code in codes_to_test:
        url = f"http://api.biyingapi.com/hszg/gg/{code}/{license_key}"
        print(f"   Testing '{name}' -> Code: {code} ... ", end="")
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, list) and len(d) > 0:
                    print(f"✅ OK ({len(d)} stocks)")
                else:
                    print(f"❌ Empty/Invalid")
            else:
                print(f"❌ HTTP {r.status_code}")
        except:
            print(f"❌ Error")

    print("\nTest Complete.")
    return True


if __name__ == "__main__":
    print("--- Biying API Connectivity Tester ---")
    if len(sys.argv) > 1:
        key = sys.argv[1]
    else:
        key = input("Please enter your Biying License Key: ").strip()
    
    if not key:
        print("No license provided. Exiting.")
    else:
        test_api(key)
        print("\nTest Complete.")
