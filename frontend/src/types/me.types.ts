/** `/me` self-service types (weaknesses, adaptive difficulty, recommendations). */

import type { Band, ConcreteDifficulty, IeltsModule } from './common.types';

export interface WeaknessItem {
  module: IeltsModule;
  tag: string;
  severity: number;
  occurrences: number;
  lastSeenAt: string;
  resolved: boolean;
  priority: number;
}

export interface WeaknessList {
  items: WeaknessItem[];
}

export interface AdaptiveDifficultyItem {
  module: IeltsModule;
  difficulty: ConcreteDifficulty;
  recentBand: Band | null;
  rationale: string;
}

export interface AdaptiveDifficultyResponse {
  modules: AdaptiveDifficultyItem[];
}

export interface Recommendation {
  module: IeltsModule;
  tag: string;
  title: string;
  action: string;
  severity: number;
  difficulty: ConcreteDifficulty;
}

export interface RecommendationsResponse {
  items: Recommendation[];
  message: string;
}
