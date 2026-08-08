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

/**
 * Minutes actually spent, not attempts counted.
 *
 * Attempt counts flatter: five two-minute taps look like more work than one
 * forty-minute essay. Minutes are what a learner is actually budgeting.
 */
export interface StudyTime {
  todayMinutes: number;
  weekMinutes: number;
  totalMinutes: number;
  dailyGoalMinutes: number;
  /** Capped at 100 — "247% of your goal" reads as a warning, not praise. */
  dailyGoalPct: number;
}

export interface DashboardData {
  studyTime: StudyTime;
  greetingName: string;
  streakDays: number;
  prediction: BandPrediction;
  coach: DailyCoachMessage;
  modules: ModuleProgress[];
  checklist: ChecklistItem[];
  checklistCompletionPct: number;
}
