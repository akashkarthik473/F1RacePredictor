"""
F1 Race Prediction Model
Predicts race results based on qualifying performance and historical data.
"""

import pickle
from pathlib import Path
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
        self.team_strength = {}  # Average points per race by team
        self.is_trained = False
    
    def _calculate_team_strength(self, df: pd.DataFrame) -> dict:
        """Calculate average points scored per race by each team."""
        return df.groupby("team")["points"].mean().to_dict()
    
    def _prepare_features(self, df: pd.DataFrame, fit_encoders: bool = False) -> np.ndarray:
        """Prepare feature matrix for model."""
        features = []
        
        # Qualifying position (most important predictor)
        features.append(df["quali_position"].values)
        
        # Team encoding
        if fit_encoders:
            team_encoded = self.team_encoder.fit_transform(df["team"])
        else:
            # Handle unseen teams
            team_encoded = []
            for team in df["team"]:
                if team in self.team_encoder.classes_:
                    team_encoded.append(self.team_encoder.transform([team])[0])
                else:
                    team_encoded.append(-1)
            team_encoded = np.array(team_encoded)
        features.append(team_encoded)
        
        # Team strength (historical performance)
        team_strength = df["team"].map(lambda t: self.team_strength.get(t, 5.0))
        features.append(team_strength.values)
        
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
        if not self.is_trained:
            # Use simple heuristic if model not trained
            return self._simple_predict(quali_data)
        
        X = self._prepare_features(quali_data, fit_encoders=False)
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
    
    def _simple_predict(self, quali_data: pd.DataFrame) -> list[RacePrediction]:
        """
        Simple prediction when model isn't trained.
        Uses quali position + team strength adjustment.
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
        
        predictions = []
        for _, row in quali_data.iterrows():
            # Base prediction is quali position
            base = row["quali_position"]
            
            # Adjust by team strength
            team_adj = default_strength.get(row["team"], 0)
            pred_pos = max(1, base - team_adj * 0.5)
            
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
            "team_strength": self.team_strength,
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
            self.team_strength = data["team_strength"]
            self.is_trained = data["is_trained"]
        return self


# Global predictor instance
predictor = F1Predictor()

# Try to load existing model
predictor.load()

