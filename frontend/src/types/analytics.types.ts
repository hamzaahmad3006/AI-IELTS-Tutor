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
