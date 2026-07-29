/** Grammar lesson domain types. */

export interface GrammarLessonSummary {
  id: string;
  title: string;
  conceptTag: string;
  summary: string;
  level: string;
  minutes: number;
  /** True when the lesson targets one of the learner's recorded weaknesses. */
  recommended: boolean;
}

export interface GrammarExample {
  incorrect?: string;
  correct?: string;
  note?: string;
}

export interface GrammarLessonDetail {
  id: string;
  title: string;
  conceptTag: string;
  summary: string;
  body: string;
  examples: GrammarExample[];
  level: string;
  minutes: number;
}

export interface GrammarLessonList {
  items: GrammarLessonSummary[];
  recommendedCount: number;
}
