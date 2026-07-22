/** Speaking module domain types. */

import type { Band } from './common.types';

export type SpeakingPart = 1 | 2 | 3;

export type SpeakingSessionStatus =
  | 'connecting'
  | 'active'
  | 'paused'
  | 'finished'
  | 'failed';

export type TranscriptSpeaker = 'examiner' | 'learner';

export type TranscriptTokenKind = 'normal' | 'strong' | 'suggestion';

export interface TranscriptToken {
  text: string;
  kind: TranscriptTokenKind;
}

export interface TranscriptEntry {
  id: string;
  speaker: TranscriptSpeaker;
  tokens: TranscriptToken[];
  isFinal: boolean;
}

export interface SpeakingSession {
  sessionId: string;
  examinerName: string;
  part: SpeakingPart;
  status: SpeakingSessionStatus;
  currentPrompt: string;
  confidenceBoost: number; // percentage 0..100
  elapsedSeconds: number;
  isMuted: boolean;
  transcript: TranscriptEntry[];
}

export interface SpeakingCriteriaScore {
  fluencyCoherence: Band;
  lexicalResource: Band;
  grammaticalRange: Band;
  pronunciation: Band;
}

export interface SpeakingResult {
  attemptId: string;
  overallBand: Band;
  criteria: SpeakingCriteriaScore;
  feedbackSummary: string;
}
