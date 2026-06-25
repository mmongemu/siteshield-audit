# Akamai Site Shield & Origin Security Auditor

A collection of professional automation utilities designed to securely map Akamai configurations, identify active **Site Shield** perimeters, and extract backend **Origin** topologies across an entire enterprise account. 

This repository includes two versions of the tool:
1. **Streamlit Web Application** (`2_SiteShield_Auditor.py`) — A highly interactive dashboard with dynamic account searching, live countdowns, visual progress bars, and data exports.
2. **Standalone CLI Utility** (`siteshield_auditor_cli.py`) — A pure terminal-based version optimized for lightweight execution on a macOS shell environment.

Both scripts implement **Recursive Tree Crawling** to locate deeply nested configuration behaviors and include **Exponential Backoff Automation** to safely recover from `429 Rate Limit` thresholds without losing data.

---
## Core Dependencies & Installation Matrix

To communicate with the Akamai Intelligent Edge platform securely, these tools rely on specific Python libraries. The requirements change depending on whether you are running the lightweight terminal scanner or the full interactive web application.

### 1. Library Frameworks Explained

* **`requests`** *(Required for BOTH)*: Handles the underlying synchronous HTTP/HTTPS communication layer to Akamai's Edge API endpoints.
* **`edgegrid-python` (`akamai-edgegrid`)** *(Required for BOTH)*: The official Akamai authentication signing library. It intercepts outgoing network hooks to generate custom cryptographically signed headers (`EG1-HMAC-SHA256`) required by Akamai API gateways.
* **`pandas`** *(Required for STREAMLIT Only)*: An advanced data parsing engine used to transform raw, heavily nested JSON config payloads into clean dataframes.
* **`streamlit`** *(Required for STREAMLIT Only)*: A web rendering engine that builds a dashboard out of a Python script on a local server.

---

### 2. Isolated Target Installation Steps

Choose the command block that matches the specific application flavor you intend to deploy:

#### Scenario A: Installing Only the Standalone CLI Utility
If you are only running the pure terminal-based version (`siteshield_auditor_cli.py`), you only need the baseline API communication stack:

```bash
# Optional: Setup and activate environment
python3 -m venv cli-env
source cli-env/bin/activate

# Install bare minimum requirements
pip install requests edgegrid-python
```

#### Scenario B: Installing the Streamlit Web Application (Fresh Setup)
If you want to run the full dashboard panel application interface (2_SiteShield_Origins.py) from scratch:

```Bash
# Create and activate environment
python3 -m venv tool-env
source tool-env/bin/activate

# Upgrade installer and install the complete dashboard stack
pip install --upgrade pip
pip install requests edgegrid-python pandas streamlit
```

#### Scenario C: Injecting into an Existing Streamlit Platform (Toolbox)
If your team already runs a virtual environment environment hosting a toolbox instance (like your active project management matrix platform), you only need to ensure the Akamai-specific calling libraries are updated inside that current runtime environment scope:

```Bash
# Activate your pre-existing environment container
source tool-env/bin/activate

# Inject the necessary core authentication components without touching streamlit/pandas
pip install requests edgegrid-python
```


### 3. Akamai API Credentials (~/.edgerc) Setup
The scripts will look for your API credentials inside a hidden configuration file in your home directory named .edgerc.

#### Step 1: Generate Tokens in Control Center
1. Log into Akamai Control Center.
2. Navigate to Identity & Access Management > API Clients.
3. Create a new API client with a minimum of the following access scopes:
- Property Manager (PAPI): Read-Only or Read-Write (Required to crawl the property rule trees).
- Identity Management: Read-Only (Required to resolve your Account Switch Keys via name search).

#### Step 2: Write the .edgerc File
Create or modify the file at ~/.edgerc using a text editor (e.g., ```nano ~/.edgerc```) and paste your tokens into the [default] section exactly like this:

```ini
[default]
client_secret = xxxxXXXXxxxxXXXXxxxxXXXXxxxxXXXXxxxxXXXX=
host = akab-xxxx-xxxx.luna.akamaiapis.net
access_token = akab-xxxx-xxxx-xxxx
client_token = akab-xxxx-xxxx-xxxx
```

--

## 1. Standalone CLI Version (```siteshield-auditor-cli.py```)
Optimized for system engineers and terminal purists who need to audit accounts without launching a browser process.

### How to Use:
1.Open your terminal and navigate to the folder containing the script.

2. Execute the Python script:
```bash
python siteshield_auditor_cli.py
```
3. Type in an account search string.

4. Select the matching account from the numbered list.

5. Confirm execution. The script will safely crawl through the property tree using a 3-second safety delay and write the final output to a clean CSV report (```siteshield_terminal_audit.csv```) in your current working directory.

## 2. Streamlit Web Version (```2_SiteShield_Auditor.py```)

The Streamlit web application provides a responsive UI, real-time metrics, dynamic countdown bars, and direct CSV downloading.

### Scenario A: You are NOT using Streamlit yet (Fresh Install)

1. Ensure your virtual environment is active:

```bash
source tool-env/bin/activate
```

2. Launch the application server:
```bash
streamlit run 2_SiteShield_Auditor.py
```

3. The application will automatically map local system ports and open inside a tab in your default browser (typically at http://localhost:8501).
   
### Scenario B: Incorporating into an Existing Multi-Page Instance
If your team already runs a multi-page Streamlit suite (such as an internal engineering platform or global portal), this script is built to plug straight in natively.

#### 1. Directory Layout Integration
Move 2_SiteShield_Origins.py directly into your pre-existing sub-routed pages/ folder:

```Plaintext
your-existing-toolbox/
│
├── Home.py                  # Your existing landing page / dashboard home
├── requirements.txt         # Global dependencies
│
└── pages/                   # Multi-page system directory
    ├── 1_Project_Matrix.py  # Pre-existing internal pages...
    └── 2_SiteShield_Auditor.py  # <-- Place this script here
```
#### 2. Automatic Integration Mechanics
- Sidebar Routing: Streamlit automatically detects files inside the pages/ directory. On your next app refresh, "2 Site Shield Origins" will instantly appear as an option in your global sidebar navigation menu.
  
- Page Ordering: The numerical prefix (2_) handles the visual order inside the sidebar navigation lists.
  
- Isolated State Configuration: The script handles its own st.set_page_config() routine and EdgeGrid client instances locally, meaning it will completely isolate its state definitions from your Home.py or other active tool tabs.

## Troubleshooting & Runtime Errors

- ```ModuleNotFoundError: No module named 'akamai'```: The ```edgegrid-python``` library is either not installed or you forgot to activate your virtual environment (```source tool-env/bin/activate```) before running.

- ```API Error 403``` / Unauthorized: Your .edgerc file path is valid, but the specific API client credentials do not have permission to read property rules for that selected Group or Contract block. Contact your Akamai administrator to elevate the API client role.

- ```API Error 400 / Missing contractId```: This is a fallback symptom of bad search scoping. Ensure you are utilizing the updated tool code, which automatically maps explicit group and contract parameters during execution loops.

- Frequent Pauses / ⚠️ ```Account Rate Limiting Encountered!```: This means the global account token bucket is running thin. Let the script sit; its automated 60-second back-off sleep cycle will resume execution safely as soon as Akamai regenerates your quota tokens.



