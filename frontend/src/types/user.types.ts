/** User profile & onboarding domain types. */

import type {
  Band,
  ExamType,
  IeltsModule,
  ProficiencyLevel,
} from './common.types';

export type UserRole = 'learner' | 'content_editor' | 'admin' | 'super_admin';

export interface LearnerProfile {
  userId: string;
  examType: ExamType;
  selfLevel: ProficiencyLevel;
  cefrLevel: string | null;
  targetBand: Band;
  examDate: string | null; // ISO date
  dailyMinutes: number;
  baselines: Record<IeltsModule, Band | null>;
  consentVoice: boolean;
  consentAi: boolean;
}

export interface OnboardingDraft {
  examType: ExamType;
  selfLevel: ProficiencyLevel;
  targetBand: Band;
  examDate: string | null;
  dailyMinutes: number;
  consentVoice: boolean;
  consentAi: boolean;
}

export interface OnboardingState {
  step: number;
  totalSteps: number;
  draft: OnboardingDraft;
}
