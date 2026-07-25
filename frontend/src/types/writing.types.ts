/** Writing module domain types. */

import type { Band } from './common.types';

export interface WritingCriteriaScore {
  taskResponse: Band;
  coherenceCohesion: Band;
  lexicalResource: Band;
  grammaticalRange: Band;
}

// ---- Backend-accurate scoring shapes (POST/GET /writing/attempts) ----
export interface WritingSubmit {
  essayText: string;
  taskType: number; // 1 | 2
  promptText?: string;
}

export interface WritingResult {
  attemptId: string;
  status: string;
  taskType: number;
  wordCount: number;
  overallBand: Band | null;
  criteria: WritingCriteriaScore | null;
  feedbackSummary: string | null;
  improvedEssay: string | null;
}

export interface WritingHistoryItem {
  attemptId: string;
  taskType: number;
  wordCount: number;
  overallBand: Band | null;
  status: string;
  createdAt: string;
}

export interface WritingHistoryPage {
  items: WritingHistoryItem[];
  nextCursor: string | null;
}

export type EssaySegmentKind = 'normal' | 'error' | 'suggestion';

export interface EssaySegment {
  text: string;
  kind: EssaySegmentKind;
}

export interface KeyImprovement {
  id: string;
  icon: string;
  title: string;
  description: string;
}

export type FeedbackTab = 'draft' | 'model';

export interface WritingFeedback {
  attemptId: string;
  taskLabel: string; // e.g. "Writing Task 2"
  title: string; // "Detailed AI Feedback"
  analysisSummary: string;
  overallBand: Band;
  bandLabel: string; // e.g. "Competent User"
  criteria: WritingCriteriaScore;
  masterTip: string;
  draftSegments: EssaySegment[];
  modelEssay: string;
  wordCount: number;
  improvements: KeyImprovement[];
}
