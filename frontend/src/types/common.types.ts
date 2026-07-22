/** Shared primitive / union types used across the domain. */

export type IeltsModule = 'speaking' | 'writing' | 'reading' | 'listening';

export type ExamType = 'academic' | 'general';

export type ProficiencyLevel = 'beginner' | 'intermediate' | 'advanced';

export type Difficulty = 'easy' | 'medium' | 'hard' | 'adaptive';

/** IELTS band value: 0–9 in 0.5 increments (validated at the boundary). */
export type Band = number;

export type LoadingStatus = 'idle' | 'loading' | 'succeeded' | 'failed';

export interface Nullable<T> {
  value: T | null;
}

/** Async slice envelope reused by Redux state shapes. */
export interface AsyncState<T> {
  data: T | null;
  status: LoadingStatus;
  error: string | null;
}
