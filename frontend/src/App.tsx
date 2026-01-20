import { useState, useEffect } from 'react';
import type {
  RacePrediction,
  ScheduleRace,
  PredictionResult,
  ManualQualiInput,
  QualifyingResult,
  QualifyingResponse,
} from './api/client';
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
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualPrediction, setManualPrediction] = useState<PredictionResult | null>(null);
  const [manualLoading, setManualLoading] = useState(false);
  const [qualiLeaderboard, setQualiLeaderboard] = useState<QualifyingResponse | null>(null);
  const [qualiLoading, setQualiLoading] = useState(false);
  const [manualQualiLeaderboard, setManualQualiLeaderboard] = useState<QualifyingResponse | null>(null);
  const [manualQualiLoading, setManualQualiLoading] = useState(false);
  
  // Manual input form state
  const [manualInput, setManualInput] = useState<ManualQualiInput>({
    driver: '',
    team: '',
    quali_time: '',
    track_name: '',
    pole_time: '',
    estimated_position: undefined,
  });

  useEffect(() => {
    checkApiHealth();
  }, []);

  useEffect(() => {
    if (apiStatus === 'online') {
      fetchSchedule();
    }
  }, [selectedYear, apiStatus]);

  // When a track is selected in manual mode, load that track's qualifying leaderboard
  useEffect(() => {
    const loadManualQuali = async () => {
      if (!showManualInput || !manualInput.track_name || apiStatus !== 'online') {
        setManualQualiLeaderboard(null);
        return;
      }

      setManualQualiLoading(true);
      try {
        const data = await api.getQualifying(selectedYear, manualInput.track_name);
        setManualQualiLeaderboard(data);
      } catch {
        setManualQualiLeaderboard(null);
      } finally {
        setManualQualiLoading(false);
      }
    };

    loadManualQuali();
  }, [showManualInput, manualInput.track_name, selectedYear, apiStatus]);

  // When a race is selected, load the qualifying leaderboard
  useEffect(() => {
    const loadQuali = async () => {
      if (!selectedRace || apiStatus !== 'online') {
        setQualiLeaderboard(null);
        return;
      }

      setQualiLoading(true);
      try {
        const data = await api.getQualifying(selectedYear, selectedRace);
        setQualiLeaderboard(data);
      } catch (err) {
        // Don't surface as a main error, just clear the leaderboard
        setQualiLeaderboard(null);
      } finally {
        setQualiLoading(false);
      }
    };

    loadQuali();
  }, [selectedRace, selectedYear, apiStatus]);

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

  const handleManualPredict = async () => {
    if (!manualInput.driver || !manualInput.team || !manualInput.quali_time || !manualInput.track_name) {
      setError('Please fill in driver, team, track, and qualifying time');
      return;
    }
    
    setManualLoading(true);
    setError(null);
    
    try {
      const result = await api.predictFromTime({
        driver: manualInput.driver,
        team: manualInput.team,
        quali_time: manualInput.quali_time,
        track_name: manualInput.track_name,
        pole_time: manualInput.pole_time || undefined,
        estimated_position: manualInput.estimated_position || undefined,
      });
      setManualPrediction(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get prediction');
    } finally {
      setManualLoading(false);
    }
  };

  const getTeamColor = (team: string): string => {
    return TEAM_COLORS[team] || '#666';
  };

  const formatLapTime = (seconds: number | null): string => {
    if (seconds === null || Number.isNaN(seconds)) return '—';
    const totalMs = Math.round(seconds * 1000);
    const mins = Math.floor(totalMs / 60000);
    const remMs = totalMs - mins * 60000;
    const secs = Math.floor(remMs / 1000);
    const ms = remMs - secs * 1000;
    const secStr = secs.toString().padStart(2, '0');
    const msStr = ms.toString().padStart(3, '0');
    return `${mins}:${secStr}.${msStr}`;
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

        {/* Toggle between race selector and manual input */}
        <section className="mode-toggle">
          <button
            className={`mode-btn ${!showManualInput ? 'active' : ''}`}
            onClick={() => {
              setShowManualInput(false);
              setManualPrediction(null);
            }}
          >
            📅 Predict from Race
          </button>
          <button
            className={`mode-btn ${showManualInput ? 'active' : ''}`}
            onClick={() => {
              setShowManualInput(true);
              setPrediction(null);
            }}
          >
            ⏱️ Enter Qualifying Time
          </button>
        </section>

        {!showManualInput ? (
          /* Race Selector */
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
            {/* Qualifying Leaderboard */}
            {selectedRace && (
              <div className="quali-leaderboard">
                <div className="quali-header">
                  <h3>Qualifying Leaderboard</h3>
                  {qualiLoading && <span className="quali-loading">Loading...</span>}
                </div>
                {qualiLeaderboard ? (
                  <table className="quali-table">
                    <thead>
                      <tr>
                        <th>P</th>
                        <th>Driver</th>
                        <th>Team</th>
                        <th>Q1</th>
                        <th>Q2</th>
                        <th>Q3</th>
                      </tr>
                    </thead>
                    <tbody>
                      {qualiLeaderboard.results.map((row: QualifyingResult) => (
                        <tr key={row.driver}>
                          <td>P{row.quali_position}</td>
                          <td>{row.driver}</td>
                          <td>{row.team}</td>
                          <td>{formatLapTime(row.q1_time)}</td>
                          <td>{formatLapTime(row.q2_time)}</td>
                          <td>{formatLapTime(row.q3_time)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : !qualiLoading ? (
                  <p className="quali-empty">No qualifying data available for this race.</p>
                ) : null}
              </div>
            )}
          </section>
        ) : (
          /* Manual Qualifying Time Input */
          <section className="manual-input-section">
            <h2>Enter Qualifying Time</h2>
            <div className="manual-input-form">
              <div className="input-group">
                <label htmlFor="driver">Driver</label>
                <input
                  id="driver"
                  type="text"
                  placeholder="e.g., VER, HAM, LEC"
                  value={manualInput.driver}
                  onChange={(e) => setManualInput({ ...manualInput, driver: e.target.value.toUpperCase() })}
                />
              </div>
              
              <div className="input-group">
                <label htmlFor="team">Team</label>
                <select
                  id="team"
                  value={manualInput.team}
                  onChange={(e) => setManualInput({ ...manualInput, team: e.target.value })}
                >
                  <option value="">Select team...</option>
                  {Object.keys(TEAM_COLORS).map(team => (
                    <option key={team} value={team}>{team}</option>
                  ))}
                </select>
              </div>
              
              <div className="input-group">
                <label htmlFor="track_name">Track/GP *</label>
                <select
                  id="track_name"
                  value={manualInput.track_name}
                  onChange={(e) => setManualInput({ ...manualInput, track_name: e.target.value })}
                >
                  <option value="">Select track...</option>
                  {schedule.map(race => (
                    <option key={race.round} value={race.name}>
                      {race.name}
                    </option>
                  ))}
                </select>
                <small>Track characteristics affect predictions</small>
              </div>
              
              <div className="input-group">
                <label htmlFor="quali_time">Qualifying Time *</label>
                <input
                  id="quali_time"
                  type="text"
                  placeholder="e.g., 1:23.456 or 83.456"
                  value={manualInput.quali_time}
                  onChange={(e) => setManualInput({ ...manualInput, quali_time: e.target.value })}
                />
                <small>Format: MM:SS.mmm or SS.mmm</small>
              </div>
              
              <div className="input-group">
                <label htmlFor="pole_time">Pole Time (Optional)</label>
                <input
                  id="pole_time"
                  type="text"
                  placeholder="e.g., 1:23.123"
                  value={manualInput.pole_time || ''}
                  onChange={(e) => setManualInput({ ...manualInput, pole_time: e.target.value })}
                />
                <small>Helps estimate qualifying position</small>
              </div>
              
              <div className="input-group">
                <label htmlFor="estimated_position">Est. Quali Position (Optional)</label>
                <input
                  id="estimated_position"
                  type="number"
                  min="1"
                  max="20"
                  placeholder="1-20"
                  value={manualInput.estimated_position || ''}
                  onChange={(e) => setManualInput({ 
                    ...manualInput, 
                    estimated_position: e.target.value ? Number(e.target.value) : undefined 
                  })}
                />
              </div>
              
              <button
                className="btn-predict"
                onClick={handleManualPredict}
                disabled={manualLoading || apiStatus !== 'online' || !manualInput.driver || !manualInput.team || !manualInput.track_name || !manualInput.quali_time}
              >
                {manualLoading ? 'Predicting...' : '🔮 Predict Race Position'}
              </button>
            </div>
            
            {manualPrediction && (
              <div className="manual-prediction-result">
                <h3>Prediction Result</h3>
                <PredictionCard
                  prediction={manualPrediction}
                  rank={1}
                  teamColor={getTeamColor(manualPrediction.team)}
                  hasActual={false}
                />
              </div>
            )}

            {/* Qualifying leaderboard for the selected track in manual mode */}
            {manualInput.track_name && (
              <div className="quali-leaderboard" style={{ marginTop: '1.5rem' }}>
                <div className="quali-header">
                  <h3>Qualifying Leaderboard ({manualInput.track_name})</h3>
                  {manualQualiLoading && <span className="quali-loading">Loading...</span>}
                </div>
                {manualQualiLeaderboard ? (
                  <table className="quali-table">
                    <thead>
                      <tr>
                        <th>P</th>
                        <th>Driver</th>
                        <th>Team</th>
                        <th>Q1</th>
                        <th>Q2</th>
                        <th>Q3</th>
                      </tr>
                    </thead>
                    <tbody>
                      {manualQualiLeaderboard.results.map((row: QualifyingResult) => (
                        <tr key={row.driver}>
                          <td>P{row.quali_position}</td>
                          <td>{row.driver}</td>
                          <td>{row.team}</td>
                          <td>{formatLapTime(row.q1_time)}</td>
                          <td>{formatLapTime(row.q2_time)}</td>
                          <td>{formatLapTime(row.q3_time)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : !manualQualiLoading ? (
                  <p className="quali-empty">No qualifying data available for this track.</p>
                ) : null}
              </div>
            )}
          </section>
        )}

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
