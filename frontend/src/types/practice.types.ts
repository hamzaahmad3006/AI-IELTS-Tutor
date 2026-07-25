/** Shared types for the objective practice modules (Reading + Listening). */

export type PracticeQuestionType =
  | 'mcq'
  | 'true_false_notgiven'
  | 'matching_headings'
  | 'short_answer'
  | 'sentence_completion'
  | 'form_completion';

/** A question as delivered to the learner — never includes the answer. */
export interface PracticeQuestion {
  id: string;
  type: PracticeQuestionType;
  prompt: string;
  options: string[] | null;
}

/** A submitted answer: a single value or (for matching) a list. */
export type AnswerValue = string | string[];

/** Map of questionId -> submitted answer. */
export type AnswerMap = Record<string, AnswerValue>;

/** Per-question grading result returned after submission. */
export interface BasePerQuestionResult {
  questionId: string;
  type: string;
  correct: boolean;
  submitted: AnswerValue | null;
  correctAnswer: AnswerValue;
  explanation: string | null;
}
