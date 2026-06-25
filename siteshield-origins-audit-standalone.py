import os
import sys
import time
import requests
import pandas as pd
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from urllib.parse import urljoin

# --- 1. AUTHENTICATION SETUP ---
EDGERC_PATH = os.path.expanduser("~/.edgerc")
SECTION = "default"

print("==================================================")
print("🛡️  AKAMAI SITE SHIELD & ORIGIN TERMINAL AUDITOR")
print("==================================================")

try:
    rc = EdgeRc(EDGERC_PATH)
    auth = EdgeGridAuth.from_edgerc(EDGERC_PATH, SECTION)
    base_url = f"https://{rc.get(SECTION, 'host')}"
    PAPI_HEADERS = {"PAPI-Use-Prefixes": "true", "Accept": "application/json"}
    print("✅ EdgeGrid Authentication Initialized Successfully.\n")
except Exception as e:
    print(f"❌ Auth Initialization Error: {e}")
    sys.exit(1)

# --- 2. RECURSIVE CRAWLING LOGIC ---
def find_siteshield_recursive(rule_node):
    for b in rule_node.get('behaviors', []):
        if b.get('name') == 'siteShield': 
            return b
    for child in rule_node.get('children', []):
        result = find_siteshield_recursive(child)
        if result: return result
    return None

def find_origins_recursive(rule_node, origin_list=None):
    if origin_list is None: 
        origin_list = []
    for b in rule_node.get('behaviors', []):
        if b.get('name') == 'origin':
            hostname = b.get('options', {}).get('hostname')
            if hostname and hostname not in origin_list: 
                origin_list.append(hostname)
    for child in rule_node.get('children', []):
        find_origins_recursive(child, origin_list)
    return origin_list

def get_all_properties(switch_key):
    all_props = []
    g_res = requests.get(urljoin(base_url, "/papi/v1/groups"), 
                         auth=auth, headers=PAPI_HEADERS, params={"accountSwitchKey": switch_key})
    
    if g_res.status_code == 200:
        groups = g_res.json().get('groups', {}).get('items', [])
        for g in groups:
            gid = g['groupId']
            for cid in g.get('contractIds', []):
                p_res = requests.get(urljoin(base_url, "/papi/v1/properties"), auth=auth, headers=PAPI_HEADERS,
                                     params={"accountSwitchKey": switch_key, "groupId": gid, "contractId": cid})
                if p_res.status_code == 200:
                    all_props.extend(p_res.json().get('properties', {}).get('items', []))
                time.sleep(1.0) 
    return all_props

# --- 3. INTERACTIVE ACCOUNT SEARCH ---
search_query = input("🔍 Search for Account Name (e.g., Hallmark): ").strip()
if len(search_query) < 3:
    print("❌ Error: Please enter at least 3 characters to search.")
    sys.exit(1)

print("📡 Querying identity profiles...")
id_url = urljoin(base_url, "/identity-management/v3/api-clients/self/account-switch-keys")
res = requests.get(id_url, auth=auth, params={"search": search_query})

selected_key = None
if res.status_code == 200:
    accounts = res.json()
    if accounts:
        print("\nDiscovered Accounts:")
        account_map = {}
        for idx, a in enumerate(accounts):
            display_str = f"[{idx + 1}] {a['accountName']} ({a['accountSwitchKey']})"
            print(display_str)
            account_map[str(idx + 1)] = a['accountSwitchKey']
        
        selection = input("\nSelect target account index number: ").strip()
        selected_key = account_map.get(selection)
    else:
        print("❌ No matching accounts discovered.")
        sys.exit(1)
else:
    print(f"❌ Account Search Failed: {res.status_code}")
    sys.exit(1)

if not selected_key:
    print("❌ Invalid selection.")
    sys.exit(1)

# --- 4. AUDIT EXECUTION ENGINE ---
print("\n🔄 Step 1: Mapping remote property directory metadata...")
raw_props = get_all_properties(selected_key)
unique_props = list({p['propertyId']: p for p in raw_props}.values())
total_count = len(unique_props)

if total_count == 0:
    print("❌ No active properties discovered under administrative scopes.")
    sys.exit(0)

print(f"✅ Discovery Complete! Found {total_count} properties to evaluate.")
confirm = input("🚀 Ready to begin audit with a 3-second safety delay? (y/n): ").strip().lower()
if confirm != 'y':
    print("Audit canceled.")
    sys.exit(0)

print("\nStarting Audit Pipeline...")
enabled_data = []

i = 0
while i < total_count:
    p = unique_props[i]
    p_id, p_name = p['propertyId'], p['propertyName']
    v_prod = p.get('productionVersion')
    
    rem_min = int(((total_count - i) * 3.5) // 60)
    print(f"[{i+1}/{total_count}] Scanning: {p_name} (Est. Remaining: ~{rem_min}m)...", end="", flush=True)
    
    if not v_prod:
        print(" [No Active Prod Version]")
        i += 1
        continue

    url = urljoin(base_url, f"/papi/v1/properties/{p_id}/versions/{v_prod}/rules")
    params = {"accountSwitchKey": selected_key, "contractId": p['contractId'], "groupId": p['groupId']}
    
    res = requests.get(url, auth=auth, headers=PAPI_HEADERS, params=params)
    
    if res.status_code == 200:
        rules_tree = res.json().get('rules', {})
        ss_block = find_siteshield_recursive(rules_tree)
        if ss_block:
            print(" -> 🛡️  ENABLED")
            opts = ss_block.get('options', {}).get('ssmap', {})
            origins = find_origins_recursive(rules_tree)
            enabled_data.append({
                "Property Name": p_name,
                "Prod Version": v_prod,
                "Map Value": opts.get('value', 'N/A'),
                "Site Shield Map": opts.get('name', 'N/A'),
                "Origins": ", ".join(origins) if origins else "None Formed"
            })
        else:
            print(" -> Skip (Disabled)")
        i += 1
        time.sleep(3.0) 
        
    elif res.status_code == 429:
        print("\n⚠️  Account Rate Limiting Encountered!")
        for wait_sec in range(60, 0, -1):
            sys.stdout.write(f"\rCooling token budget window... Res