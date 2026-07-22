/** Home dashboard domain types. */

import type { Band, IeltsModule } from './common.types';

export interface BandPrediction {
  predictedBand: Band;
  confidence: number; // 0..1
  distanceToTarget: number;
  basedOnSessions: number;
  progressToTarget: number; // 0..1 for the progress bar
}

export interface ModuleProgress {
  module: IeltsModule;
  currentLevel: Band;
  isActive: boolean;
}

export interface DailyCoachMessage {
  id: string;
  title: string;
  message: string;
}

export type ChecklistPriority = 'low' | 'medium' | 'high';

export interface ChecklistItem {
  id: string;
  title: string;
  subtitle: string;
  isCompleted: boolean;
  completedAt: string | null;
  priority: ChecklistPriority | null;
}

export interface DashboardData {
  greetingName: string;
  streakDays: number;
  prediction: BandPrediction;
  coach: DailyCoachMessage;
  modules: ModuleProgress[];
  checklist: ChecklistItem[];
  checklistCompletionPct: number;
}
