/** Writing module domain types. */

import type { Band } from './common.types';

export interface WritingCriteriaScore {
  taskResponse: Band;
  coherenceCohesion: Band;
  lexicalResource: Band;
  grammaticalRange: Band;
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
