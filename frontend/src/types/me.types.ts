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

/**
 * Recursive JSON type. The data export contains whole database rows whose
 * shapes are the backend's business, so this models "arbitrary JSON" precisely
 * rather than reaching for `any`/`unknown`.
 */
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface DataExportAccount {
  id: string;
  email: string;
  fullName: string;
  role: string;
  emailVerified: boolean;
  createdAt: string;
}

export interface DataExport {
  exportedAt: string;
  account: DataExportAccount;
  profile: JsonValue;
  writingAttempts: JsonValue[];
  speakingAttempts: JsonValue[];
  readingAttempts: JsonValue[];
  listeningAttempts: JsonValue[];
  weaknesses: JsonValue[];
  vocabReviews: JsonValue[];
}

export interface DeleteAccountResponse {
  deleted: boolean;
  /** Rows removed per table, so deletion is verifiable rather than asserted. */
  removed: Record<string, number>;
}
