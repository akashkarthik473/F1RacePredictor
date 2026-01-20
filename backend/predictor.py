"""
F1 Race Prediction Model
Predicts race results based on qualifying performance and historical data.
"""

import pickle
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from dataclasses import dataclass

MODEL_PATH = Path(__file__).parent / "f1_model.pkl"


@dataclass
class RacePrediction:
    driver: str
    team: str
    quali_position: int
    predicted_position: int
    confidence: float
    expected_points: float


class F1Predictor:
    """
    Predicts F1 race results based on qualifying data.
    
    Features used:
    - Qualifying position
    - Team performance (encoded)
    - Q3 time gap to pole (if available)
    - Historical grid-to-finish statistics
    """
    
    def __init__(self):
        self.model = None
        self.team_encoder = LabelEncoder()
        self.track_encoder = LabelEncoder()
        self.team_strength = {}  # Average points per race by team
        self.track_overtaking_difficulty = {}  # Track-specific overtaking difficulty (0-1)
        self.is_trained = False
    
    def _calculate_team_strength(self, df: pd.DataFrame) -> dict:
        """Calculate average points scored per race by each team."""
        return df.groupby("team")["points"].mean().to_dict()
    
    def _calculate_track_overtaking_difficulty(self, df: pd.DataFrame) -> dict:
        """
        Calculate track-specific overtaking difficulty based on average position change.
        Lower values = easier to overtake, higher values = harder to overtake.
        """
        if "position_change" in df.columns and "race_name" in df.columns:
            # Average position change per track (positive = gained positions)
            track_stats = df.groupby("race_name")["position_change"].mean()
            # Normalize to 0-1 scale (invert so higher = harder to overtake)
            max_change = track_stats.max()
            min_change = track_stats.min()
            if max_change != min_change:
                normalized = 1 - (track_stats - min_change) / (max_change - min_change)
            else:
                normalized = pd.Series(0.5, index=track_stats.index)
            return normalized.to_dict()
        return {}
    
    def _prepare_features(self, df: pd.DataFrame, fit_encoders: bool = False) -> np.ndarray:
        """Prepare feature matrix for model."""
        features = []
        
        # Qualifying position (most important predictor)
        features.append(df["quali_position"].values)
        
        # Team encoding
        if fit_encoders:
            team_encoded = self.team_encoder.fit_transform(df["team"])
        else:
            # If encoder was never fitted (e.g., loaded from older model), fall back gracefully
            if not hasattr(self.team_encoder, "classes_"):
                team_encoded = np.full(len(df), -1)
            else:
                # Handle unseen teams
                encoded: list[int] = []
                for team in df["team"]:
                    if team in self.team_encoder.classes_:
                        encoded.append(self.team_encoder.transform([team])[0])
                    else:
                        encoded.append(-1)
                team_encoded = np.array(encoded)
        features.append(team_encoded)
        
        # Team strength (historical performance)
        team_strength = df["team"].map(lambda t: self.team_strength.get(t, 5.0))
        features.append(team_strength.values)
        
        # Track encoding (if available)
        if "race_name" in df.columns:
            if fit_encoders:
                track_encoded = self.track_encoder.fit_transform(df["race_name"])
            else:
                if not hasattr(self.track_encoder, "classes_"):
                    track_encoded = np.full(len(df), -1)
                else:
                    encoded_tracks: list[int] = []
                    for track in df["race_name"]:
                        if track in self.track_encoder.classes_:
                            encoded_tracks.append(self.track_encoder.transform([track])[0])
                        else:
                            encoded_tracks.append(-1)
                    track_encoded = np.array(encoded_tracks)
            features.append(track_encoded)
            
            # Track overtaking difficulty
            track_difficulty = df["race_name"].map(
                lambda t: self.track_overtaking_difficulty.get(t, 0.5)
            )
            features.append(track_difficulty.values)
        
        # Q3 time (if available) - gap to fastest
        if "q3_time" in df.columns:
            q3_times = df["q3_time"].fillna(df["q3_time"].max() + 5)
            q3_gap = q3_times - q3_times.min()
            features.append(q3_gap.values)
        
        return np.column_stack(features)
    
    def train(self, training_data: pd.DataFrame):
        """
        Train the prediction model on historical data.
        
        Args:
            training_data: DataFrame with columns:
                - quali_position, team, q3_time (features)
                - race_position (target)
        """
        # Filter out DNFs and incomplete data
        df = training_data[
            (training_data["race_position"].notna()) & 
            (training_data["race_position"] <= 20)
        ].copy()
        
        # Calculate team strength
        self.team_strength = self._calculate_team_strength(df)
        
        # Calculate track overtaking difficulty
        self.track_overtaking_difficulty = self._calculate_track_overtaking_difficulty(df)
        
        # Prepare features and target
        X = self._prepare_features(df, fit_encoders=True)
        y = df["race_position"].values
        
        # Train model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X, y)
        self.is_trained = True
        
        # Save model
        self.save()
        
        return self
    
    def predict(self, quali_data: pd.DataFrame) -> list[RacePrediction]:
        """
        Predict race results from qualifying data.
        
        Args:
            quali_data: DataFrame with quali results (driver, team, quali_position, q3_time)
        
        Returns:
            List of RacePrediction objects sorted by predicted position
        """
        if not self.is_trained or self.model is None:
            # Use simple heuristic if model not trained
            return self._simple_predict(quali_data)
        
        X = self._prepare_features(quali_data, fit_encoders=False)

        # Handle models trained before track features were added
        if hasattr(self.model, "n_features_in_"):
            expected_features = int(self.model.n_features_in_)  # type: ignore[attr-defined]
            if X.shape[1] != expected_features:
                # If we have more features now (e.g., added track features), keep the first N
                if X.shape[1] > expected_features:
                    X = X[:, :expected_features]
                # If we somehow have fewer, pad with zeros
                elif X.shape[1] < expected_features:
                    pad = np.zeros((X.shape[0], expected_features - X.shape[1]))
                    X = np.hstack([X, pad])

        raw_predictions = self.model.predict(X)
        
        # Convert to predictions
        predictions = []
        for i, row in quali_data.iterrows():
            pred_pos = raw_predictions[i] if isinstance(i, int) else raw_predictions[quali_data.index.get_loc(i)]
            
            # Calculate confidence based on quali position (higher quali = more certain)
            confidence = max(0.3, 1.0 - (row["quali_position"] - 1) * 0.03)
            
            # Expected points based on predicted position
            points = self._position_to_points(round(pred_pos))
            
            predictions.append(RacePrediction(
                driver=row["driver"],
                team=row["team"],
                quali_position=int(row["quali_position"]),
                predicted_position=int(round(pred_pos)),
                confidence=round(confidence, 2),
                expected_points=points
            ))
        
        # Sort by predicted position
        predictions.sort(key=lambda p: p.predicted_position)
        return predictions
    
    def predict_from_time(
        self, 
        driver: str, 
        team: str, 
        quali_time_seconds: float, 
        track_name: str,
        pole_time_seconds: Optional[float] = None,
        estimated_position: Optional[int] = None
    ) -> RacePrediction:
        """
        Predict race position from a single driver's qualifying time.
        
        Args:
            driver: Driver name/abbreviation
            team: Team name
            quali_time_seconds: Qualifying time in seconds
            track_name: Track/GP name (e.g., "Monaco Grand Prix", "Bahrain Grand Prix")
            pole_time_seconds: Pole position time in seconds (optional, for gap calculation)
            estimated_position: Estimated qualifying position (optional, if known)
        
        Returns:
            RacePrediction for the single driver
        """
        # If position not provided, estimate from time gap
        if estimated_position is None:
            if pole_time_seconds is not None:
                # Estimate position based on time gap (rough approximation)
                time_gap = quali_time_seconds - pole_time_seconds
                # Typical gaps: P1=0s, P2=0.1-0.3s, P3=0.2-0.5s, etc.
                # Rough estimate: 0.15s per position
                estimated_position = max(1, min(20, int(round(1 + time_gap / 0.15))))
            else:
                # Default to mid-field if no reference
                estimated_position = 10
        
        # Create a single-row DataFrame with track information
        quali_df = pd.DataFrame({
            "driver": [driver],
            "team": [team],
            "quali_position": [estimated_position],
            "q3_time": [quali_time_seconds],
            "race_name": [track_name]
        })
        
        # Use existing predict method
        predictions = self.predict(quali_df)
        
        if predictions:
            return predictions[0]
        else:
            # Fallback if prediction fails
            return RacePrediction(
                driver=driver,
                team=team,
                quali_position=estimated_position,
                predicted_position=estimated_position,
                confidence=0.5,
                expected_points=self._position_to_points(estimated_position)
            )
    
    def _simple_predict(self, quali_data: pd.DataFrame) -> list[RacePrediction]:
        """
        Simple prediction when model isn't trained.
        Uses quali position + team strength adjustment + track difficulty.
        """
        # Default team strengths (rough 2024 estimates)
        default_strength = {
            "Red Bull Racing": 2.0,
            "Ferrari": 1.5,
            "McLaren": 1.5,
            "Mercedes": 1.0,
            "Aston Martin": 0.5,
            "Alpine": 0.0,
            "Williams": -0.5,
            "RB": -0.5,
            "Kick Sauber": -1.0,
            "Haas F1 Team": -1.0,
        }
        
        # Track-specific adjustments (harder to overtake = less position change)
        # Monaco, Singapore, Hungary are harder to overtake
        track_adjustments = {
            "Monaco Grand Prix": 0.3,  # Hard to overtake, quali position more important
            "Singapore Grand Prix": 0.2,
            "Hungarian Grand Prix": 0.2,
            "Bahrain Grand Prix": -0.1,  # Easier to overtake
            "Austrian Grand Prix": -0.1,
            "Brazilian Grand Prix": -0.1,
        }
        
        predictions = []
        for _, row in quali_data.iterrows():
            # Base prediction is quali position
            base = row["quali_position"]
            
            # Adjust by team strength
            team_adj = default_strength.get(row["team"], 0)
            pred_pos = max(1, base - team_adj * 0.5)
            
            # Adjust by track difficulty if available
            if "race_name" in row and pd.notna(row["race_name"]):
                track_adj = track_adjustments.get(row["race_name"], 0)
                # Positive adjustment = harder to overtake = stay closer to quali position
                pred_pos = max(1, pred_pos + track_adj * (row["quali_position"] - 1))
            
            confidence = max(0.3, 1.0 - (row["quali_position"] - 1) * 0.03)
            
            predictions.append(RacePrediction(
                driver=row["driver"],
                team=row["team"],
                quali_position=int(row["quali_position"]),
                predicted_position=int(round(pred_pos)),
                confidence=round(confidence, 2),
                expected_points=self._position_to_points(int(round(pred_pos)))
            ))
        
        predictions.sort(key=lambda p: p.predicted_position)
        return predictions
    
    def _position_to_points(self, position: int) -> float:
        """Convert race position to F1 points."""
        points_map = {
            1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
            6: 8, 7: 6, 8: 4, 9: 2, 10: 1
        }
        return points_map.get(position, 0)
    
    def save(self):
        """Save trained model to disk."""
        data = {
            "model": self.model,
            "team_encoder": self.team_encoder,
            "track_encoder": self.track_encoder,
            "team_strength": self.team_strength,
            "track_overtaking_difficulty": self.track_overtaking_difficulty,
            "is_trained": self.is_trained
        }
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(data, f)
    
    def load(self):
        """Load trained model from disk."""
        if MODEL_PATH.exists():
            with open(MODEL_PATH, "rb") as f:
                data = pickle.load(f)
            self.model = data["model"]
            self.team_encoder = data["team_encoder"]
            self.track_encoder = data.get("track_encoder", LabelEncoder())
            self.team_strength = data["team_strength"]
            self.track_overtaking_difficulty = data.get("track_overtaking_difficulty", {})
            self.is_trained = data["is_trained"]
        return self


# Global predictor instance
predictor = F1Predictor()

# Try to load existing model
predictor.load()

