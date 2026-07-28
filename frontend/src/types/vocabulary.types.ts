/** Vocabulary (spaced repetition) domain types. */

export interface VocabCard {
  itemId: string;
  word: string;
  definition: string;
  example: string | null;
  lexicalField: string | null;
  cefrLevel: string | null;
  isNew: boolean;
}

export interface VocabQueue {
  items: VocabCard[];
  dueCount: number;
  newCount: number;
}

/** SM-2 grade: 0-2 = failed recall, 3-5 = successful. */
export type VocabGrade = 0 | 1 | 2 | 3 | 4 | 5;

export interface VocabGradeResult {
  itemId: string;
  repetitions: number;
  intervalDays: number;
  easeFactor: number;
  dueAt: string;
  totalReviews: number;
}

export interface VocabStats {
  totalItems: number;
  started: number;
  dueNow: number;
  mastered: number;
}
