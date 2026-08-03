/** Full mock test types (mirror `/mock-tests`). */

import type { Band, IeltsModule } from './common.types';

export interface MockSection {
  module: IeltsModule;
  minutes: number;
}

export interface MockTest {
  id: string;
  status: string;
  sections: MockSection[];
  passageId: string | null;
  clipId: string | null;
  writingPromptId: string | null;
  cueCardId: string | null;
  totalMinutes: number;
}

export interface MockSubmission {
  readingAnswers: Record<string, string>;
  listeningAnswers: Record<string, string>;
  writingText: string | null;
  speakingText: string | null;
}

export interface ModuleReadiness {
  module: IeltsModule;
  band: Band | null;
  gap: number | null;
  verdict: string;
}

export interface ReadinessReport {
  overallBand: Band | null;
  targetBand: Band;
  verdict: string;
  headline: string;
  modules: ModuleReadiness[];
  weakestModule: IeltsModule | null;
  advice: string;
}

export interface MockResult {
  id: string;
  status: string;
  overallBand: Band | null;
  readiness: ReadinessReport;
}
