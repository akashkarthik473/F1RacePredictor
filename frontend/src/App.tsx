import { useState, useEffect } from 'react';
import type { RacePrediction, ScheduleRace, PredictionResult } from './api/client';
import { api } from './api/client';
import './App.css';

// Team colors for visual distinction
const TEAM_COLORS: Record<string, string> = {
  'Red Bull Racing': '#3671C6',
  'Ferrari': '#E8002D',
  'McLaren': '#FF8000',
  'Mercedes': '#27F4D2',
  'Aston Martin': '#229971',
  'Alpine': '#FF87BC',
  'Williams': '#64C4FF',
  'RB': '#6692FF',
  'Kick Sauber': '#52E252',
  'Haas F1 Team': '#B6BABD',
};

function App() {
  const [schedule, setSchedule] = useState<ScheduleRace[]>([]);
  const [selectedYear, setSelectedYear] = useState(2024);
  const [selectedRace, setSelectedRace] = useState<number | null>(null);
  const [prediction, setPrediction] = useState<RacePrediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [modelTrained, setModelTrained] = useState(false);
  const [training, setTraining] = useState(false);

  useEffect(() => {
    checkApiHealth();
  }, []);

  useEffect(() => {
    if (apiStatus === 'online') {
      fetchSchedule();
    }
  }, [selectedYear, apiStatus]);

  const checkApiHealth = async () => {
    try {
      const health = await api.healthCheck();
      setApiStatus('online');
      setModelTrained(health.model_trained);
    } catch {
      setApiStatus('offline');
    }
  };

  const fetchSchedule = async () => {
    try {
      const data = await api.getSchedule(selectedYear);
      setSchedule(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch schedule');
    }
  };

  const handlePrediction = async () => {
    if (!selectedRace) return;
    
    console.log(`[DEBUG] Fetching prediction for year=${selectedYear}, race=${selectedRace}`);
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await api.getPrediction(selectedYear, selectedRace);
      console.log(`[DEBUG] Received prediction for: ${data.race} (${data.year})`);
      setPrediction(data);
      setModelTrained(data.model_trained);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get prediction');
    } finally {
      setLoading(false);
    }
  };

  const handleTrainModel = async () => {
    setTraining(true);
    setError(null);
    
    try {
      await api.trainModel('2024');
      
      // Poll for training completion (training can take several minutes)
      const pollInterval = setInterval(async () => {
        try {
          const status = await api.getModelStatus();
          if (status.is_trained) {
            setModelTrained(true);
            setTraining(false);
            clearInterval(pollInterval);
          }
        } catch {
          // Keep polling
        }
      }, 3000); // Check every 3 seconds
      
      // Stop polling after 5 minutes max
      setTimeout(() => {
        clearInterval(pollInterval);
        setTraining(false);
      }, 300000);
      
    } catch (err) {
      setError('Failed to start training');
      setTraining(false);
    }
  };

  const getTeamColor = (team: string): string => {
    return TEAM_COLORS[team] || '#666';
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return 'TBD';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="app">
      <div className="background-pattern"></div>
      
      <header className="header">
        <div className="logo">
          <span className="logo-icon">🏎️</span>
          <h1>F1 Race Predictor</h1>
        </div>
        <div className={`status-badge ${apiStatus}`}>
          <span className="status-dot"></span>
          {apiStatus === 'checking' ? 'Connecting...' : apiStatus === 'online' ? 'API Online' : 'API Offline'}
        </div>
      </header>

      <main className="main">
        {/* Model Status */}
        <section className="model-status">
          <div className={`model-badge ${modelTrained ? 'trained' : 'untrained'}`}>
            {modelTrained ? '✓ Model Trained' : '⚠ Model Not Trained'}
          </div>
          {!modelTrained && (
            <button 
              className="btn-train" 
              onClick={handleTrainModel}
              disabled={training || apiStatus !== 'online'}
            >
              {training ? 'Training...' : 'Train Model (2024 data)'}
            </button>
          )}
        </section>

        {/* Race Selector */}
        <section className="selector-section">
          <h2>Select Race</h2>
          <div className="selector-controls">
            <select 
              className="year-select"
              value={selectedYear}
              onChange={(e) => {
                setSelectedYear(Number(e.target.value));
                setSelectedRace(null);
                setPrediction(null);
              }}
            >
              {[2024, 2023, 2022].map(year => (
                <option key={year} value={year}>{year} Season</option>
              ))}
            </select>
            
            <select 
              className="race-select"
              value={selectedRace || ''}
              onChange={(e) => setSelectedRace(Number(e.target.value))}
            >
              <option value="">Choose a race...</option>
              {schedule.map(race => (
                <option key={race.round} value={race.round}>
                  R{race.round}: {race.name} ({formatDate(race.date)})
                </option>
              ))}
            </select>
            
            <button 
              className="btn-predict"
              onClick={handlePrediction}
              disabled={!selectedRace || loading || apiStatus !== 'online'}
            >
              {loading ? 'Predicting...' : '🔮 Predict Race'}
            </button>
          </div>
        </section>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <span>⚠️</span> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Predictions */}
        {prediction && (
          <section className="predictions-section">
            <div className="predictions-header">
              <h2>{prediction.race} {prediction.year}</h2>
              <div className="prediction-tags">
                <span className="prediction-tag">
                  {prediction.model_trained ? 'ML Prediction' : 'Heuristic Prediction'}
                </span>
                {prediction.has_actual_results && (
                  <span className="prediction-tag actual">✓ Actual Results Available</span>
                )}
              </div>
            </div>

            <div className="predictions-grid">
              {prediction.predictions.map((p, index) => (
                <PredictionCard 
                  key={p.driver} 
                  prediction={p} 
                  rank={index + 1}
                  teamColor={getTeamColor(p.team)}
                  hasActual={prediction.has_actual_results}
                />
              ))}
            </div>
          </section>
        )}

        {/* Info Section */}
        {!prediction && apiStatus === 'online' && (
          <section className="info-section">
            <div className="info-card">
              <span className="info-icon">📊</span>
              <h3>How It Works</h3>
              <p>
                Select a race weekend to predict the race results based on qualifying performance.
                The model analyzes qualifying times, team performance, and historical data.
              </p>
            </div>
            <div className="info-card">
              <span className="info-icon">🎯</span>
              <h3>Prediction Factors</h3>
              <ul>
                <li>Qualifying position</li>
                <li>Team historical performance</li>
                <li>Lap time gaps</li>
                <li>Track characteristics</li>
              </ul>
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <p>Built with FastF1 + FastAPI + React</p>
      </footer>
    </div>
  );
}

// Prediction Card Component
function PredictionCard({ 
  prediction, 
  rank, 
  teamColor,
  hasActual
}: { 
  prediction: PredictionResult; 
  rank: number;
  teamColor: string;
  hasActual: boolean;
}) {
  const predictedPos = Math.round(prediction.predicted_position);
  const actualPos = prediction.actual_position;
  
  // Calculate prediction accuracy (how many positions off)
  const predictionError = hasActual && actualPos 
    ? predictedPos - actualPos 
    : null;
  
  // Was prediction correct (within 1 position)?
  const isAccurate = predictionError !== null && Math.abs(predictionError) <= 1;
  
  return (
    <div 
      className={`prediction-card ${hasActual ? 'has-actual' : ''} ${isAccurate ? 'accurate' : ''}`}
      style={{ 
        borderLeftColor: teamColor,
        animationDelay: `${rank * 0.05}s`
      }}
    >
      <div className="prediction-rank">
        <span className="rank-number">{rank}</span>
        {rank <= 3 && <span className="rank-emoji">{rank === 1 ? '🥇' : rank === 2 ? '🥈' : '🥉'}</span>}
      </div>
      
      <div className="prediction-driver">
        <span className="driver-name">{prediction.driver}</span>
        <span className="driver-team" style={{ color: teamColor }}>{prediction.team}</span>
      </div>
      
      <div className="prediction-stats">
        <div className="stat">
          <span className="stat-label">Quali</span>
          <span className="stat-value">P{prediction.quali_position}</span>
        </div>
        <div className="stat predicted">
          <span className="stat-label">Predicted</span>
          <span className="stat-value">P{prediction.predicted_position}</span>
        </div>
        {hasActual && (
          <>
            <div className="stat actual">
              <span className="stat-label">Actual</span>
              <span className="stat-value">
                {actualPos ? `P${actualPos}` : 'DNF'}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Error</span>
              <span className={`stat-value ${predictionError !== null ? (predictionError === 0 ? 'perfect' : Math.abs(predictionError) <= 2 ? 'close' : 'off') : ''}`}>
                {predictionError !== null 
                  ? (predictionError === 0 ? '✓' : predictionError > 0 ? `+${predictionError}` : predictionError)
                  : '-'
                }
              </span>
            </div>
          </>
        )}
        {!hasActual && (
          <div className="stat">
            <span className="stat-label">Exp. Pts</span>
            <span className="stat-value">{prediction.expected_points}</span>
          </div>
        )}
        {hasActual && (
          <div className="stat points-compare">
            <span className="stat-label">Points</span>
            <span className="stat-value">
              <span className="predicted-pts">{prediction.expected_points}</span>
              <span className="pts-arrow">→</span>
              <span className="actual-pts">{prediction.actual_points ?? 0}</span>
            </span>
          </div>
        )}
      </div>
      
      <div className="confidence-bar">
        <div 
          className="confidence-fill" 
          style={{ width: `${prediction.confidence * 100}%` }}
        />
      </div>
    </div>
  );
}

export default App;
