import os
import requests
import streamlit as st
import pandas as pd
import time
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from urllib.parse import urljoin

# --- MUST BE THE FIRST STREAMLIT COMMAND ---
st.set_page_config(page_title="Site Shield & Origin Auditor", layout="wide", page_icon="🛡️")

# --- AKAMAI BRANDING DESIGN ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
    }
    
    .stButton > button {
        background-color: #0099CC !important;
        color: white !important;
        border-radius: 2px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #004B87 !important; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
    }
    
    div[data-testid="stMetricValue"] {
        color: #0099CC !important; 
        font-weight: 700 !important;
        font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    div[data-testid="stMetricLabel"] {
        color: #555555 !important;
        font-weight: 600 !important;
    }
    
    .akamai-corporate-banner {
        height: 5px;
        background-color: #0099CC !important;
        margin-bottom: 20px;
        border-radius: 2px;
    }
    </style>
""", unsafe_allow_html=True)

def render_akamai_header():
    st.markdown('<div class="akamai-corporate-banner"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 8])
    with col1:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_logo_path = os.path.join(current_dir, "akamai_blue_logo.png")
        if os.path.exists(local_logo_path):
            st.image(local_logo_path, width=165)
        else:
            st.markdown("<span style='color:#002244; font-weight:800; font-size:24px;'>Akamai</span>", unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <h1 style="font-family: 'Segoe UI', Roboto, Helvetica, sans-serif; font-size: 32px; font-weight: 800; color: #002244; margin: 0; padding-top: 5px;">
                Site Shield & Origin Control Directory
            </h1>
        """, unsafe_allow_html=True)
    st.markdown('<div style="border-bottom: 1px solid #EFEFEF; margin-bottom: 20px; padding-bottom: 10px;"></div>', unsafe_allow_html=True)

# --- INITIAL RUNTIME BANNER ---
render_akamai_header()

# --- AUTHENTICATION CONFIGURATION ---
EDGERC_PATH = os.path.expanduser("~/.edgerc")
SECTION = "default"

try:
    rc = EdgeRc(EDGERC_PATH)
    auth = EdgeGridAuth.from_edgerc(EDGERC_PATH, SECTION)
    base_url = f"https://{rc.get(SECTION, 'host')}"
    PAPI_HEADERS = {"PAPI-Use-Prefixes": "true", "Accept": "application/json"}
except Exception as e:
    st.error(f"❌ Auth Initialization Error: {e}")
    st.stop()

# --- RECURSIVE CORE LOGIC ---
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

# --- ACCOUNT LOOKUP INTERFACE ---
st.subheader("📁 Account Directory Configuration")
search_query = st.text_input("🔍 Search for Account Name to Target:", placeholder="e.g. Hallmark")
selected_key = None

if search_query and len(search_query) >= 3:
    id_url = urljoin(base_url, "/identity-management/v3/api-clients/self/account-switch-keys")
    res = requests.get(id_url, auth=auth, params={"search": search_query})
    
    if res.status_code == 200:
        accounts = res.json()
        if accounts:
            account_options = {f"{a['accountName']} ({a['accountSwitchKey']})": a['accountSwitchKey'] for a in accounts}
            choice = st.selectbox("Select Target Scope Account:", options=list(account_options.keys()))
            selected_key = account_options[choice]
        else:
            st.warning("No accounts discovered matching that specific criteria naming convention.")

st.divider()

# --- RUN AUDIT EXECUTION ENGINE ---
if selected_key:
    if st.button("🚀 Run Site Shield & Origin Audit"):
        # INSTANT FEEDBACK LAYER TO ENTIRELY RESOLVE BUTTON DELAY SENSATION
        st.toast("Scan Core Initiated!", icon="🚀")
        placeholder = st.empty()
        
        with placeholder.container():
            st.info("📡 Connecting securely to EdgeGrid context... Mapping remote endpoint discovery rules.")
            raw_props = get_all_properties(selected_key)
            unique_props = list({p['propertyId']: p for p in raw_props}.values())
            total_count = len(unique_props)

        if total_count == 0:
            st.error("No valid customer profiles discovered under specified administrative scopes.")
        else:
            st.success(f"Discovery Complete! Identified **{total_count}** tracking properties to scan.")
            
            enabled_data = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            retry_text = st.empty()
            
            i = 0
            while i < total_count:
                p = unique_props[i]
                p_id, p_name = p['propertyId'], p['propertyName']
                v_prod = p.get('productionVersion')
                
                # Accurately compute upcoming timing projections dynamically
                rem_min = int(((total_count - i) * 3.5) // 60)
                status_text.markdown(f"**Scanning {i+1}/{total_count}:** `{p_name}`  \n*Est. time remaining: ~{rem_min}m*")
                
                if not v_prod:
                    i += 1
                    continue

                url = urljoin(base_url, f"/papi/v1/properties/{p_id}/versions/{v_prod}/rules")
                params = {"accountSwitchKey": selected_key, "contractId": p['contractId'], "groupId": p['groupId']}
                
                res = requests.get(url, auth=auth, headers=PAPI_HEADERS, params=params)
                
                if res.status_code == 200:
                    retry_text.empty()
                    rules_tree = res.json().get('rules', {})
                    ss_block = find_siteshield_recursive(rules_tree)
                    if ss_block:
                        opts = ss_block.get('options', {}).get('ssmap', {})
                        origins = find_origins_recursive(rules_tree)
                        enabled_data.append({
                            "Property Name": p_name,
                            "Prod Version": v_prod,
                            "Map Value": opts.get('value', 'N/A'),
                            "Site Shield Map": opts.get('name', 'N/A'),
                            "Origins": ", ".join(origins) if origins else "None Formed"
                        })
                    i += 1 
                    time.sleep(3.0) 
                
                elif res.status_code == 429:
                    for wait_sec in range(60, 0, -1):
                        retry_text.warning(f"⚠️ Account Rate Limiting Encountered! Cooling token budget window... Resuming execution path inside {wait_sec}s")
                        time.sleep(1)
                else:
                    i += 1 
                
                progress_bar.progress(i / total_count)

            status_text.empty()
            st.balloons()
            
            # Formatted Output Display Component 
            st.subheader("📈 Operational Profile Assessment")
            st.metric("Site Shield Deployment Coverage", f"{len(enabled_data)} / {total_count} Active Routes")
            
            if enabled_data:
                df_clean = pd.DataFrame(enabled_data)
                st.dataframe(df_clean, use_container_width=True, hide_index=True)
                
                csv_payload = df_clean.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Clean Audit Dataset (CSV)", 
                    data=csv_payload, 
                    file_name="siteshield_origin_audit_results.csv", 
                    mime="text/csv"
                )