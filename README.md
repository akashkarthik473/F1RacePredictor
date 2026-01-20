# FastF1 - FastAPI + React Fullstack App

A modern fullstack application with a FastAPI backend and React + TypeScript frontend.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white)

## 📁 Project Structure

```
fastF1/
├── backend/
│   ├── main.py           # FastAPI application
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts # API client for backend communication
│   │   ├── App.tsx       # Main React component
│   │   ├── App.css       # Styles
│   │   └── main.tsx      # Entry point
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** - For the backend
- **Node.js 18+** - For the frontend

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the server:
   ```bash
   python main.py
   ```
   
   Or use uvicorn directly:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

The API will be available at `http://localhost:8000`

📖 **API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger docs

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The app will be available at `http://localhost:5173`

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Welcome message |
| GET | `/api/health` | Health check |
| GET | `/api/items` | Get all items |
| GET | `/api/items/{id}` | Get item by ID |
| POST | `/api/items` | Create new item |
| PUT | `/api/items/{id}` | Update item |
| DELETE | `/api/items/{id}` | Delete item |

## 🛠️ Development

### Running Both Services

You'll need two terminal windows:

**Terminal 1 - Backend:**
```bash
cd backend
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Building for Production

**Frontend:**
```bash
cd frontend
npm run build
```

The build output will be in `frontend/dist/`

## ✨ Features

- ⚡ **FastAPI** - High-performance Python backend
- ⚛️ **React 18** - Modern React with hooks
- 📘 **TypeScript** - Type-safe frontend code
- 🎨 **Custom UI** - Beautiful dark theme with animations
- 🔄 **Hot Reload** - Both backend and frontend support hot reloading
- 📝 **Auto Docs** - Swagger UI at `/docs`
- 🔗 **CORS Configured** - Ready for frontend-backend communication

## 📝 License

MIT

