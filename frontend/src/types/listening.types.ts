/** Listening module domain types (mirror the backend `/listening` responses). */

import type { Band, Difficulty, ExamType } from './common.types';
import type {
  AnswerMap,
  BasePerQuestionResult,
  PracticeQuestion,
} from './practice.types';

export interface ListeningClip {
  id: string;
  title: string;
  audioUrl: string;
  durationSec: number;
  examType: ExamType;
  difficulty: Difficulty;
  accent: string | null;
  questions: PracticeQuestion[];
}

export interface ListeningSubmit {
  audioId: string;
  answers: AnswerMap;
}

export interface ListeningPerQuestionResult extends BasePerQuestionResult {
  answerTimestamp: string | null;
}

export interface ListeningResult {
  attemptId: string;
  audioId: string;
  rawScore: number;
  totalQuestions: number;
  band: Band;
  perQuestion: ListeningPerQuestionResult[];
}

export interface ListeningHistoryItem {
  attemptId: string;
  audioId: string | null;
  rawScore: number;
  totalQuestions: number;
  band: Band;
  createdAt: string;
}

export interface ListeningHistoryPage {
  items: ListeningHistoryItem[];
  nextCursor: string | null;
}
