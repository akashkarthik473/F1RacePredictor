## F1 Race Predictor 🏎️  

**End‑to‑end F1 race prediction app** using live timing data from FastF1, a FastAPI backend, an ML model in Python, and a React + TypeScript frontend.

The app lets you:
- **Predict race results** from a selected weekend’s qualifying session
- **Compare predictions vs actual race results** (when available)
- **Enter custom qualifying times** and estimate where a driver is likely to finish

---

### 📁 Project Structure

```text
F1RacePredictor/
├── backend/
│   ├── main.py          # FastAPI application & REST API
│   ├── predictor.py     # ML model wrapper + prediction logic
│   ├── f1_data.py       # Utilities to load FastF1 timing data
│   ├── quali_models.py  # (Additional) qualifying / model helpers
│   ├── requirements.txt # Python dependencies
│   └── f1_cache/        # Local FastF1 HTTP/data cache (ignored in Git)
├── frontend/
│   ├── src/
│   │   ├── api/client.ts # Typed API client for the backend
│   │   ├── App.tsx       # Main React UI
│   │   ├── App.css       # F1‑style dark UI
│   │   └── main.tsx      # React entrypoint
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

### 🧠 How the Model Works (High Level)

The backend model (`predictor.py`) uses **qualifying performance and historical race data** to predict race results:

- **Features**  
  - Qualifying position  
  - Team (label‑encoded)  
  - Track name and overtaking difficulty  
  - Q3 lap time gaps (when available)  
  - Historical team strength (average points per race)  

- **Model**  
  - `GradientBoostingRegressor` from scikit‑learn  
  - Trained on historical seasons loaded via FastF1 and cached locally  
  - Falls back to a **heuristic model** if the ML model is not yet trained

The API exposes predictions as structured JSON that the React frontend visualizes in cards with confidence bars, team colors, and (when available) actual race results for comparison.

---

### 🚀 Getting Started

#### Prerequisites

- **Python 3.10+** – backend / model
- **Node.js 18+** – frontend

---

### 🐍 Backend Setup (FastAPI + FastF1)

1. **Navigate to the backend directory**

```bash
cd backend
```

2. **Create and activate a virtual environment** (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the API**

```bash
python main.py
# or:
uvicorn main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

- **Interactive docs (Swagger/OpenAPI)**: `http://localhost:8000/docs`

---

### ⚛️ Frontend Setup (React + Vite + TypeScript)

1. **Navigate to the frontend directory**

```bash
cd frontend
```

2. **Install dependencies**

```bash
npm install
```

3. **Start the dev server**

```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

> The frontend uses `http://localhost:8000/api` as its API base URL (see `src/api/client.ts`), so make sure the backend is running.

---

### 🔌 Key API Endpoints

All endpoints are rooted at `/api` (see `backend/main.py`):

| Method | Endpoint                          | Description |
|--------|-----------------------------------|-------------|
| GET    | `/api/health`                     | Basic health check & model status |
| GET    | `/api/schedule?year=2024`         | F1 race schedule for a season |
| GET    | `/api/predict/{year}/{race}`      | Predict race results from qualifying data |
| POST   | `/api/train?years=2023,2024`      | Train the ML model on historical seasons |
| GET    | `/api/latest-quali`               | Most recent qualifying session leaderboard |
| GET    | `/api/quali/{year}/{race}`        | Qualifying times + positions for a race |
| GET    | `/api/model-status`               | Check whether the model is trained |
| POST   | `/api/predict-from-time`          | Predict from a manually entered qualifying time |

Use the interactive docs at `/docs` to explore endpoints and payloads.

---

### 🛠️ Running Backend & Frontend Together

In two terminals:

```bash
# Terminal 1 – backend
cd backend
python main.py

# Terminal 2 – frontend
cd frontend
npm run dev
```

Then open `http://localhost:5173` in your browser.

---

### ✨ Features / What to Highlight on a Resume

- **End‑to‑end system** – FastF1 data ingestion, ML model training, REST API, and a modern React UI  
- **ML‑driven predictions** – Gradient boosting model over qualifying + historical performance features  
- **Interactive UI** – Race selector, manual time input, qualifying leaderboard, and prediction cards with team colors and confidence bars  
- **Real‑world domain** – Uses real F1 data and handles tracks, seasons, and race weekends  
- **FastF1 caching** – Local cache (`backend/f1_cache/`) to avoid repeatedly hitting remote data sources  

---

### 📝 License

MIT
