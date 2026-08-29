# Rural Business Advisory Assistant 🌾

An AI-powered Retrieval-Augmented Generation (RAG) system designed to generate hyper-local business feasibility reports for rural entrepreneurs in Mehsana District, Gujarat. 

By combining static MSME registration data, agricultural knowledge graphs, live mapping APIs, and Generative AI, this system provides actionable insights into market saturation, local competition, crop supply chains, and government financial schemes.

## 🚀 Key Features
* **Hyper-Local Competitor Mapping:** Filters registered enterprises using a static Udyam/MSME dataset to provide exact competitor counts and benchmark profiles at the Taluka level.
* **Live Map Fallback Engine:** Automatically pivots to the **Geoapify Places API** to fetch real-time local businesses if a niche query returns zero matches in the static database.
* **Agricultural Knowledge Graph:** Uses a **NetworkX** graph to link specific talukas and villages to their primary crops for supply-chain strategies.
* **Intelligent Scheme Matching:** Recommends highly relevant government financing schemes (PMEGP, PM MUDRA, GBCDC).
* **AI Report Synthesis:** Feeds the structured context into the **Google Gemini API** to generate professional, formatted business advisory reports.

## 🏗️ Tech Stack
* **Language:** Python 3.9+
* **Vector Database:** ChromaDB
* **Graph Database:** NetworkX
* **APIs:** Google Gemini API, Geoapify Places API

---

## ⚙️ Step-by-Step Installation & Setup

Follow these steps exactly to get the project running on your local machine.

### Step 1: Clone the Repository
Open your terminal or command prompt and run:
`git clone https://github.com/yourusername/Rural-Business-Advisory-Assistant.git`
`cd Rural-Business-Advisory-Assistant/backend`

### Step 2: Create a Virtual Environment (venv)
It is best practice to keep your Python packages isolated. 

**For Windows:**
`python -m venv venv`
`venv\Scripts\activate`

**For Mac/Linux:**
`python3 -m venv venv`
`source venv/bin/activate`

### Step 3: Install Dependencies
With your virtual environment active, install all required packages from the requirements.txt file:
`pip install -r requirements.txt`

### Step 4: Set Your API Keys
The system requires two API keys to function in full LLM + Live Map mode.

**For Windows (CMD):**
`set GEMINI_API_KEY=your_gemini_api_key_here`
`set GEOAPIFY_API_KEY=your_geoapify_api_key_here`

**For Windows (PowerShell):**
`$env:GEMINI_API_KEY="your_gemini_api_key_here"`
`$env:GEOAPIFY_API_KEY="your_geoapify_api_key_here"`

**For Mac/Linux:**
`export GEMINI_API_KEY="your_gemini_api_key_here"`
`export GEOAPIFY_API_KEY="your_geoapify_api_key_here"`

---

## 💻 How to Run

Make sure your virtual environment is activated and your API keys are set, then start the interactive assistant:

`python gemini_integration.py`

### Example Test Cases to Try:
1. **Idea:** `cotton yarn spinning mill` | **Taluka:** `Kadi` *(Tests high saturation & graph data)*
2. **Idea:** `book store` | **Taluka:** `Unjha` *(Tests Geoapify live fallback)*
3. **Idea:** `agricultural drone repair` | **Taluka:** `Satlasana` *(Tests niche market reasoning)*
