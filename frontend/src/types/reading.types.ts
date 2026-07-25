/** Reading module domain types (mirror the backend `/reading` responses). */

import type { Band, Difficulty, ExamType } from './common.types';
import type {
  AnswerMap,
  BasePerQuestionResult,
  PracticeQuestion,
} from './practice.types';

export interface ReadingPassage {
  id: string;
  title: string;
  body: string;
  examType: ExamType;
  difficulty: Difficulty;
  topic: string | null;
  wordCount: number;
  questions: PracticeQuestion[];
}

export interface ReadingSubmit {
  passageId: string;
  answers: AnswerMap;
}

export type ReadingPerQuestionResult = BasePerQuestionResult;

export interface ReadingResult {
  attemptId: string;
  passageId: string;
  rawScore: number;
  totalQuestions: number;
  band: Band;
  perQuestion: ReadingPerQuestionResult[];
}

export interface ReadingHistoryItem {
  attemptId: string;
  passageId: string | null;
  rawScore: number;
  totalQuestions: number;
  band: Band;
  createdAt: string;
}

export interface ReadingHistoryPage {
  items: ReadingHistoryItem[];
  nextCursor: string | null;
}
