/** Analytics domain types (mirror the backend `/analytics` responses). */

import type { Band, IeltsModule } from './common.types';

export interface ModuleProgressStat {
  module: IeltsModule;
  attempts: number;
  currentBand: Band | null;
  averageBand: Band | null;
}

export interface ProgressResponse {
  modules: ModuleProgressStat[];
  overallBand: Band | null;
  totalAttempts: number;
}

/** One scored attempt on the band timeline. `at` is an ISO-8601 timestamp. */
export interface TrendPoint {
  at: string;
  band: Band;
}

export interface ModuleTrend {
  module: IeltsModule;
  points: TrendPoint[];
}

export interface TrendResponse {
  modules: ModuleTrend[];
  /** Running overall band recomputed after each attempt, oldest first. */
  overall: TrendPoint[];
}

export interface PredictionModules {
  speaking: Band | null;
  writing: Band | null;
  reading: Band | null;
  listening: Band | null;
}

export interface PredictionResponse {
  predictedOverall: Band | null;
  confidence: number;
  horizonDate: string | null;
  modules: PredictionModules;
  velocityPerWeek: PredictionModules;
  note: string;
}
