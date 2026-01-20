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
}

export const api = new ApiClient();
