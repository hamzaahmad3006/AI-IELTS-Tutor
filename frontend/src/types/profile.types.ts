/** Onboarding + profile API types (mirror the backend `/onboarding` & `/profile`). */

import type {
  Band,
  ExamType,
  IeltsModule,
  ProficiencyLevel,
} from './common.types';

export type ModuleBaselines = Record<IeltsModule, Band | null>;

export interface OnboardingRequest {
  examType: ExamType;
  selfLevel: ProficiencyLevel;
  targetBand: Band;
  examDate: string | null;
  dailyMinutes: number;
  consentVoice: boolean;
  consentAi: boolean;
}

export interface ProfileResponse {
  userId: string;
  examType: ExamType;
  selfLevel: ProficiencyLevel;
  cefrLevel: string | null;
  targetBand: Band;
  examDate: string | null;
  dailyMinutes: number;
  baselines: ModuleBaselines;
  consentVoice: boolean;
  consentAi: boolean;
}

export type ProfileUpdate = Partial<OnboardingRequest>;
