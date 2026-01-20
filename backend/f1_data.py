"""
FastF1 Data Collection Module
Fetches historical qualifying and race data for prediction model training.
"""

import fastf1
import pandas as pd
from pathlib import Path
import logging

# Set FastF1 log level (INFO shows download progress, WARNING reduces noise)
logging.basicConfig(level=logging.WARNING, format='%(message)s')
fastf1.logger.set_log_level('WARNING')

# Enable FastF1 cache (speeds up subsequent data loads)
CACHE_DIR = Path(__file__).parent / "f1_cache"
CACHE_DIR.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))


def get_event_name(year: int, round_number: int) -> str:
    """
    Get the event name for a round number.
    FastF1's get_session can be inconsistent with round numbers,
    so we resolve to event name first.
    """
    schedule = fastf1.get_event_schedule(year)
    event = schedule[schedule["RoundNumber"] == round_number]
    if not event.empty:
        return event.iloc[0]["EventName"]
    raise ValueError(f"No event found for round {round_number} in {year}")


def get_session_data(year: int, race: str | int, session_type: str) -> pd.DataFrame:
    """
    Fetch session data for a specific race.
    
    Args:
        year: Season year (e.g., 2023)
        race: Race name or round number (e.g., "Monaco" or 7)
        session_type: "Q" for qualifying, "R" for race
    
    Returns:
        DataFrame with driver results
    """
    # If race is a round number (int or numeric string), resolve to event name
    if isinstance(race, int):
        race = get_event_name(year, race)
    elif isinstance(race, str) and race.isdigit():
        race = get_event_name(year, int(race))
    
    print(f"[DEBUG] get_session_data: year={year}, race={race}, session={session_type}", flush=True)
    
    session = fastf1.get_session(year, race, session_type)
    # Only load results, skip heavy telemetry/weather data (MUCH faster!)
    session.load(telemetry=False, weather=False, messages=False)
    return session.results


def get_qualifying_data(year: int, race: str | int) -> pd.DataFrame:
    """Get qualifying results for a race."""
    results = get_session_data(year, race, "Q")
    
    # Extract relevant columns
    quali_df = results[["DriverNumber", "Abbreviation", "TeamName", 
                        "Position", "Q1", "Q2", "Q3"]].copy()
    quali_df.columns = ["driver_number", "driver", "team", 
                        "quali_position", "q1_time", "q2_time", "q3_time"]
    
    # Convert timedelta to seconds
    for col in ["q1_time", "q2_time", "q3_time"]:
        quali_df[col] = quali_df[col].dt.total_seconds()
    
    return quali_df


def get_race_data(year: int, race: str | int) -> pd.DataFrame:
    """Get race results for a race."""
    results = get_session_data(year, race, "R")
    
    # Extract relevant columns
    race_df = results[["DriverNumber", "Abbreviation", "TeamName",
                       "Position", "GridPosition", "Status", "Points"]].copy()
    race_df.columns = ["driver_number", "driver", "team",
                       "race_position", "grid_position", "status", "points"]
    
    return race_df


def get_race_weekend_data(year: int, race: str | int) -> pd.DataFrame:
    """
    Get combined qualifying + race data for a weekend.
    This is the core data for our prediction model.
    """
    quali = get_qualifying_data(year, race)
    race = get_race_data(year, race)
    
    # Merge on driver
    combined = quali.merge(race, on=["driver_number", "driver", "team"])
    
    # Calculate position change
    combined["position_change"] = combined["grid_position"] - combined["race_position"]
    
    return combined


def get_season_data(year: int) -> pd.DataFrame:
    """
    Get race data for a season.
    Used for training the prediction model.
    
    Args:
        year: Season year
    """
    schedule = fastf1.get_event_schedule(year)
    
    # Filter to only completed races (conventional rounds)
    completed_races = schedule[schedule["EventFormat"] != "testing"]
    
    # Limit number of races for faster training
    all_data = []
    for _, event in completed_races.iterrows():
        try:
            race_data = get_race_weekend_data(year, event["RoundNumber"])
            race_data["year"] = year
            race_data["round"] = event["RoundNumber"]
            race_data["race_name"] = event["EventName"]
            all_data.append(race_data)
            print(f"    [OK] Loaded {event['EventName']}", flush=True)
        except Exception as e:
            print(f"    [FAIL] {event['EventName']}: {e}", flush=True)
            continue
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def get_current_season_schedule() -> list[dict]:
    """Get the schedule for the current/upcoming season."""
    from datetime import datetime
    year = datetime.now().year
    
    schedule = fastf1.get_event_schedule(year)
    
    races = []
    for _, event in schedule.iterrows():
        if event["EventFormat"] == "testing":
            continue
        races.append({
            "round": int(event["RoundNumber"]),
            "name": event["EventName"],
            "country": event["Country"],
            "date": event["EventDate"].isoformat() if pd.notna(event["EventDate"]) else None,
        })
    
    return races


def get_latest_qualifying(year: int = None, race: str | int = None) -> dict:
    """
    Get the most recent qualifying results.
    If no params provided, gets the latest completed qualifying session.
    """
    from datetime import datetime
    
    if year is None:
        year = datetime.now().year
    
    if race is None:
        # Find the most recent race with qualifying data
        schedule = fastf1.get_event_schedule(year)
        today = pd.Timestamp.now()
        
        # Get past events
        past_events = schedule[schedule["Session5Date"] < today]
        if past_events.empty:
            raise ValueError("No completed races found this season")
        
        race = past_events.iloc[-1]["RoundNumber"]
    
    quali = get_qualifying_data(year, race)
    
    return {
        "year": year,
        "race": race,
        "results": quali.to_dict(orient="records")
    }

