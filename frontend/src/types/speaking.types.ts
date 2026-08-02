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

export interface CueCard {
  id: string;
  topic: string;
  prompt: string;
  bulletPoints: string[];
  difficulty: string;
  prepSeconds: number;
  speakSeconds: number;
}

export interface SpeakingSubmit {
  transcript: string;
  part?: SpeakingPart;
  durationSec?: number;
}

export interface SpeakingResult {
  attemptId: string;
  status: string;
  part: SpeakingPart | null;
  overallBand: Band | null;
  criteria: SpeakingCriteriaScore | null;
  feedbackSummary: string | null;
  /** The scored transcript, so highlight offsets refer to known text. */
  transcript: string;
  issues: TranscriptIssue[];
}

export interface SpeakingHistoryItem {
  attemptId: string;
  part: SpeakingPart | null;
  overallBand: Band | null;
  status: string;
  createdAt: string;
}

export interface SpeakingHistoryPage {
  items: SpeakingHistoryItem[];
  nextCursor: string | null;
}

export interface TranscriptIssue {
  start: number;
  end: number;
  quote: string;
  tag: string;
  note: string;
}

export interface SpeakingQuestionItem {
  id: string;
  orderIndex: number;
  question: string;
}

export interface SpeakingQuestionSet {
  part: SpeakingPart;
  topic: string;
  difficulty: string;
  questions: SpeakingQuestionItem[];
  /** How this part should be answered — Part 1 and Part 3 differ. */
  guidance: string;
}
