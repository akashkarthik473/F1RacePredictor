const API_BASE_URL = 'http://localhost:8000/api';

// === Types ===

export type PredictionResult = {
  driver: string;
  team: string;
  quali_position: number;
  predicted_position: number;  // integer
  confidence: number;
  expected_points: number;
  actual_position: number | null;
  actual_points: number | null;
};

export type RacePrediction = {
  year: number;
  race: string;
  predictions: PredictionResult[];
  model_trained: boolean;
  has_actual_results: boolean;
};

export type ScheduleRace = {
  round: number;
  name: string;
  country: string;
  date: string | null;
};

export type ModelStatus = {
  is_trained: boolean;
  team_strengths: Record<string, number> | null;
};

export type HealthCheck = {
  status: string;
  timestamp: string;
  model_trained: boolean;
};

export type QualifyingResult = {
  driver: string;
  team: string;
  quali_position: number;
  q1_time: number | null;
  q2_time: number | null;
  q3_time: number | null;
};

export type QualifyingResponse = {
  year: number;
  race: string;
  results: QualifyingResult[];
};

export type ManualQualiInput = {
  driver: string;
  team: string;
  quali_time: string;
  track_name: string;
  pole_time?: string | null;
  estimated_position?: number | null;
};

// === API Client ===

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Health check
  async healthCheck(): Promise<HealthCheck> {
    return this.request<HealthCheck>('/health');
  }

  // Get race schedule
  async getSchedule(year?: number): Promise<ScheduleRace[]> {
    const url = year ? `/schedule?year=${year}` : '/schedule';
    return this.request<ScheduleRace[]>(url);
  }

  // Get race prediction
  async getPrediction(year: number, race: number | string): Promise<RacePrediction> {
    return this.request<RacePrediction>(`/predict/${year}/${race}`);
  }

  // Train the model
  async trainModel(years: string = '2023,2024'): Promise<{ status: string; message: string }> {
    return this.request(`/train?years=${years}`, { method: 'POST' });
  }

  // Get model status
  async getModelStatus(): Promise<ModelStatus> {
    return this.request<ModelStatus>('/model-status');
  }

  // Get latest qualifying
  async getLatestQualifying(): Promise<{
    year: number;
    race: number | string;
    results: Array<{
      driver: string;
      team: string;
      quali_position: number;
    }>;
  }> {
    return this.request('/latest-quali');
  }

  // Get qualifying leaderboard for a specific race
  async getQualifying(
    year: number,
    race: number | string
  ): Promise<QualifyingResponse> {
    return this.request<QualifyingResponse>(`/quali/${year}/${race}`);
  }

  // Predict from manual qualifying time
  async predictFromTime(input: ManualQualiInput): Promise<PredictionResult> {
    return this.request<PredictionResult>('/predict-from-time', {
      method: 'POST',
      body: JSON.stringify(input),
    } as RequestInit);
  }
}

export const api = new ApiClient();
