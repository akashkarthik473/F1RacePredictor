from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import pandas as pd

app = FastAPI(
    title="FastF1 Race Predictor API",
    description="Predict F1 race results from qualifying times",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---
class PredictionResult(BaseModel):
    driver: str
    team: str
    quali_position: int
    predicted_position: int
    confidence: float
    expected_points: float
    actual_position: Optional[int] = None  # Actual race finish position
    actual_points: Optional[float] = None  # Actual points scored


class RacePredictionResponse(BaseModel):
    year: int
    race: str
    predictions: list[PredictionResult]
    model_trained: bool
    has_actual_results: bool = False  # Whether actual race results are available


class TrainingStatus(BaseModel):
    status: str
    message: str
    is_trained: bool


class ScheduleRace(BaseModel):
    round: int
    name: str
    country: str
    date: Optional[str]


class ManualQualiInput(BaseModel):
    driver: str
    team: str
    quali_time: str  # Format: "MM:SS.mmm" or "SS.mmm" or seconds as float
    track_name: str  # Track/GP name (e.g., "Monaco Grand Prix", "Bahrain Grand Prix")
    pole_time: Optional[str] = None  # Optional pole time for reference
    estimated_position: Optional[int] = None  # Optional estimated quali position


# --- Routes ---
@app.get("/")
async def root():
    return {
        "message": "Welcome to FastF1 Race Predictor API",
        "docs": "/docs",
        "endpoints": {
            "schedule": "/api/schedule",
            "predict": "/api/predict/{year}/{race}",
            "predict_from_time": "/api/predict-from-time",
            "train": "/api/train",
        }
    }


@app.get("/api/health")
async def health_check():
    from predictor import predictor
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_trained": predictor.is_trained
    }


@app.get("/api/schedule", response_model=list[ScheduleRace])
async def get_schedule(year: Optional[int] = None):
    """Get the F1 race schedule for a season."""
    import fastf1
    
    if year is None:
        year = datetime.now().year
    
    try:
        schedule = fastf1.get_event_schedule(year)
        races = []
        for _, event in schedule.iterrows():
            if event["EventFormat"] == "testing":
                continue
            races.append(ScheduleRace(
                round=int(event["RoundNumber"]),
                name=event["EventName"],
                country=event["Country"],
                date=event["EventDate"].isoformat() if pd.notna(event["EventDate"]) else None,
            ))
        return races
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schedule: {str(e)}")


@app.get("/api/predict/{year}/{race}", response_model=RacePredictionResponse)
async def predict_race(year: int, race: int | str):
    """
    Predict race results based on qualifying data.
    
    - **year**: Season year (e.g., 2024)
    - **race**: Round number or race name (e.g., 1 or "Bahrain")
    """
    from f1_data import get_qualifying_data, get_race_data
    from predictor import predictor
    
    print(f"[DEBUG] Predict request: year={year}, race={race}", flush=True)
    
    try:
        # Get race name from schedule
        from f1_data import get_event_name
        if isinstance(race, int):
            race_name = get_event_name(year, race)
        elif isinstance(race, str) and race.isdigit():
            race_name = get_event_name(year, int(race))
        else:
            race_name = str(race)
        
        # Get qualifying data
        quali_df = get_qualifying_data(year, race)
        
        # Add race name to dataframe for track-specific predictions
        quali_df["race_name"] = race_name
        
        # Get predictions
        predictions = predictor.predict(quali_df)
        
        # Try to get actual race results
        actual_results = {}
        has_actual = False
        try:
            race_df = get_race_data(year, race)
            has_actual = True
            # Create lookup by driver abbreviation
            for _, row in race_df.iterrows():
                actual_results[row["driver"]] = {
                    "position": int(row["race_position"]) if pd.notna(row["race_position"]) else None,
                    "points": float(row["points"]) if pd.notna(row["points"]) else 0
                }
        except Exception:
            # Race hasn't happened yet or data unavailable
            pass
        
        # Convert to response format
        prediction_results = [
            PredictionResult(
                driver=p.driver,
                team=p.team,
                quali_position=p.quali_position,
                predicted_position=p.predicted_position,
                confidence=p.confidence,
                expected_points=p.expected_points,
                actual_position=actual_results.get(p.driver, {}).get("position"),
                actual_points=actual_results.get(p.driver, {}).get("points")
            )
            for p in predictions
        ]
        
        print(f"[DEBUG] Returning prediction for: {race_name} ({year})", flush=True)
        
        return RacePredictionResponse(
            year=year,
            race=race_name,
            predictions=prediction_results,
            model_trained=predictor.is_trained,
            has_actual_results=has_actual
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/api/train", response_model=TrainingStatus)
async def train_model(
    years: str = "2023,2024"
):
    """
    Train the prediction model on historical data.
    
    - **years**: Comma-separated list of years to train on (e.g., "2022,2023,2024")
    """
    from predictor import predictor
    from f1_data import get_season_data
    import traceback
    
    print(f"\n{'='*50}", flush=True)
    print(f"[TRAIN] Endpoint hit - years: {years}", flush=True)
    print(f"{'='*50}\n", flush=True)
    
    try:
        year_list = [int(y.strip()) for y in years.split(",")]
        
        all_data = []
        for year in year_list:
            try:
                print(f"[LOADING] {year} season data...", flush=True)
                season_data = get_season_data(year)
                all_data.append(season_data)
                print(f"[OK] Loaded {year}: {len(season_data)} records", flush=True)
            except Exception as e:
                print(f"[ERROR] Failed to load {year}: {e}", flush=True)
                traceback.print_exc()
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            print(f"[TRAINING] Model on {len(combined)} total records...", flush=True)
            predictor.train(combined)
            print(f"[SUCCESS] Model trained! is_trained={predictor.is_trained}", flush=True)
            
            return TrainingStatus(
                status="training_complete",
                message=f"Model trained on {len(combined)} records!",
                is_trained=True
            )
        else:
            print("[ERROR] No data loaded, cannot train model", flush=True)
            return TrainingStatus(
                status="failed",
                message="No data could be loaded",
                is_trained=False
            )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid year format. Use comma-separated years.")


@app.get("/api/latest-quali")
async def get_latest_qualifying():
    """Get the most recent qualifying results."""
    from f1_data import get_latest_qualifying

    try:
        return get_latest_qualifying()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch qualifying: {str(e)}")


@app.get("/api/quali/{year}/{race}")
async def get_qualifying_leaderboard(year: int, race: int | str):
    """
    Get the qualifying leaderboard (with raw times) for a specific race.

    - **year**: Season year (e.g., 2024)
    - **race**: Round number or race name (e.g., 1 or "Bahrain")
    """
    from f1_data import get_qualifying_data, get_event_name

    try:
        # Resolve race name for response
        if isinstance(race, int):
            race_name = get_event_name(year, race)
        elif isinstance(race, str) and race.isdigit():
            race_name = get_event_name(year, int(race))
        else:
            race_name = str(race)

        quali_df = get_qualifying_data(year, race)

        # Build response with seconds (frontend will format as MM:SS.mmm)
        results = []
        for _, row in quali_df.sort_values("quali_position").iterrows():
            results.append(
                {
                    "driver": row["driver"],
                    "team": row["team"],
                    "quali_position": int(row["quali_position"]),
                    "q1_time": float(row["q1_time"]) if pd.notna(row["q1_time"]) else None,
                    "q2_time": float(row["q2_time"]) if pd.notna(row["q2_time"]) else None,
                    "q3_time": float(row["q3_time"]) if pd.notna(row["q3_time"]) else None,
                }
            )

        return {
            "year": year,
            "race": race_name,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch qualifying leaderboard: {str(e)}")


@app.get("/api/model-status")
async def model_status():
    """Check if the prediction model is trained."""
    from predictor import predictor
    
    return {
        "is_trained": predictor.is_trained,
        "team_strengths": predictor.team_strength if predictor.is_trained else None
    }


def parse_time_to_seconds(time_str: str) -> float:
    """
    Parse time string to seconds.
    Supports formats:
    - "MM:SS.mmm" (e.g., "1:23.456")
    - "SS.mmm" (e.g., "83.456")
    - "SS" (e.g., "83")
    """
    time_str = time_str.strip()
    
    # Try MM:SS.mmm format
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
    
    # Try SS.mmm or SS format
    return float(time_str)


@app.post("/api/predict-from-time", response_model=PredictionResult)
async def predict_from_quali_time(input_data: ManualQualiInput):
    """
    Predict race position from a manual qualifying time input.
    
    - **driver**: Driver name/abbreviation (e.g., "VER", "HAM")
    - **team**: Team name (e.g., "Red Bull Racing", "Mercedes")
    - **quali_time**: Qualifying time in format "MM:SS.mmm" or "SS.mmm" (e.g., "1:23.456" or "83.456")
    - **track_name**: Track/GP name (e.g., "Monaco Grand Prix", "Bahrain Grand Prix")
    - **pole_time**: Optional pole position time for better position estimation
    - **estimated_position**: Optional estimated qualifying position (1-20)
    """
    from predictor import predictor
    
    try:
        # Parse times to seconds
        quali_seconds = parse_time_to_seconds(input_data.quali_time)
        pole_seconds = None
        if input_data.pole_time:
            pole_seconds = parse_time_to_seconds(input_data.pole_time)
        
        # Get prediction
        prediction = predictor.predict_from_time(
            driver=input_data.driver,
            team=input_data.team,
            quali_time_seconds=quali_seconds,
            track_name=input_data.track_name,
            pole_time_seconds=pole_seconds,
            estimated_position=input_data.estimated_position
        )
        
        return PredictionResult(
            driver=prediction.driver,
            team=prediction.team,
            quali_position=prediction.quali_position,
            predicted_position=prediction.predicted_position,
            confidence=prediction.confidence,
            expected_points=prediction.expected_points
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
