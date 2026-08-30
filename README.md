# Rural Business Advisory Assistant 🌾

An AI-powered web platform and Retrieval-Augmented Generation (RAG) system that generates hyper-local business feasibility reports for rural entrepreneurs in Mehsana District, Gujarat.

The application combines **63,900+ registered MSME records**, an **agricultural knowledge graph (NetworkX)**, **government loan scheme catalogs (PMEGP, Mudra, Stand-Up India)**, and **Generative AI** inside a full-stack **FastAPI** web application.

---

## 🚀 Key Features

* **Interactive Web Platform:** Modern responsive web interface with dashboard metrics, sector blueprints, and real-time AI advisory workspace.
* **JSON-Backed User Authentication:** Secure registration and login flow stored persistently in `database/users.json` with cryptographic salting and duplicate email detection.
* **Hyper-Local Competitor Mapping:** Analyzes 63,900+ registered MSME records to provide competitor counts, density indicators, and sample operating enterprises across all 9 Mehsana talukas (*Kadi, Visnagar, Unjha, Kheralu, Vadnagar, Vijapur, Becharaji, Satlasana, Mahesana*).
* **Agricultural Knowledge Graph:** NetworkX graph linking talukas and villages to local crop yields (Cotton, Mustard, Wheat, Bajri, Castor) for raw material sourcing insights.
* **Government Scheme & Subsidy Finder:** Matches business categories with relevant financial schemes and subsidies up to 35% (PMEGP, Mudra Tarun/Kishore, Stand-Up India, GSCDC, GBCDC).
* **Robust Offline Fallback:** Gracefully falls back to local deterministic GraphRAG advisory if Gemini API quotas or external connections are unavailable.
* **Live Map Integration:** Optional Geoapify fallback for niche businesses not found in static records.

---

## 🏗️ Tech Stack

* **Backend Framework:** FastAPI & Uvicorn (ASGI)
* **Frontend:** Jinja2 Templates, HTML5, Vanilla CSS & JavaScript (Modern DM Sans / Outfit design system)
* **Data & AI Engines:** ChromaDB, NetworkX, Pandas, Scikit-learn, Sentence-Transformers
* **LLM Integration:** Google Gemini API (with local graph/rule-based fallback)
* **Database:** JSON-based persistent user store (`database/users.json`) and cleaned CSV datasets

---

## 📁 Project Structure

```text
Rural-Business-Advisory-Assistant/
├── backend/                        # AI & RAG advisory engine
│   ├── advisory_assistant.py       # Core advisory orchestrator & context builder
│   ├── gemini_integration.py       # Gemini API caller with fallback chain
│   ├── match_schemes.py            # Government scheme matching logic
│   ├── shortlist_competitors.py    # MSME keyword & vector similarity search
│   ├── geoapify_integration.py     # Live mapping fallback
│   ├── mehsana_graph.pkl           # Pre-built NetworkX knowledge graph
│   └── msme_clean.csv              # Cleaned Mehsana MSME registry dataset
├── database/                       # Database files and user manager
│   ├── user_manager.py             # User authentication and JSON CRUD operations
│   └── users.json                  # Persistent registered user store
├── static/                         # Static web assets
│   ├── css/
│   │   ├── style.css               # Core styling tokens
│   │   └── professional.css        # Modern UI layout & components
│   └── js/
│       └── chat.js                 # Interactive chat controller & markdown renderer
├── templates/                      # Jinja2 HTML templates
│   ├── accounts/
│   │   ├── login.html              # Login page
│   │   └── register.html           # Account registration page
│   ├── chatbot/
│   │   └── chat.html               # AI Business Advisor interface
│   ├── dashboard/
│   │   └── home.html               # Main dashboard & sector blueprints
│   └── base.html                   # Base layout template
├── main.py                         # Main FastAPI application entry point
├── requirements.txt                # Python dependencies
└── .env                            # Environment variables (API keys)
```

---

## ⚙️ Installation & Setup

### Step 1: Clone the Repository
```powershell
git clone https://github.com/yourusername/Rural-Business-Advisory-Assistant.git
cd Rural-Business-Advisory-Assistant
```

### Step 2: Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

**Mac/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create or verify the `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEOAPIFY_API_KEY=your_geoapify_api_key_here
```

*(Note: The system works out-of-the-box in local mode even without external API keys).*

---

## 💻 Running the Web Application

Start the FastAPI application with Uvicorn:

```powershell or terminal
python -m uvicorn main:app --reload
```

> **Keep this terminal window open** while using the web application.

---

## 🌐 Navigating the Website

Once the server is running, open your web browser:

| Page | URL | Description |
| :--- | :--- | :--- |
| **🏠 Dashboard** | [http://localhost:8000/](http://localhost:8000/) | Overview of MSME metrics and quick-launch blueprints |
| **💬 AI Advisor** | [http://localhost:8000/chat](http://localhost:8000/chat) | Interactive advisor chat *(requires login)* |
| **🔐 Log in** | [http://localhost:8000/login](http://localhost:8000/login) | User login page |
| **📝 Register** | [http://localhost:8000/register](http://localhost:8000/register) | Account registration with duplicate email validation |
| **📖 API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger UI API documentation |

---

## 🧪 Example Test Inquiries

Try these prompts in the AI Advisor chat:

1. **Dairy Sector:**  
   `I want to start a dairy processing unit in Kadi`  
   *(Analyzes 200+ local competitors, PMEGP/Mudra loans, and local milk/crop supply).*

2. **Textile & Weaving:**  
   `Setting up a textile and cloth weaving business in Visnagar`  
   *(Identifies Visnagar textile density and Stand-Up India / PMEGP eligibility).*

3. **Food Processing:**  
   `Planning to start a spice processing and flour mill in Unjha`  
   *(Highlights Unjha APMC market context, cumin/mustard crops, and subsidies).*

4. **Retail:**  
   `Opening a general grocery and kirana shop in Kheralu`  
   *(Assesses retail saturation in Kheralu and MUDRA loan tiers).*

5. **Missing Location:**  
   `I want to open a bakery and confectionery shop`  
   *(Prompts user to select from the 9 Mehsana talukas).*
