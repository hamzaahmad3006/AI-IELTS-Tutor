/**
 * Spoken interview types.
 *
 * These mirror the backend's examiner state machine exactly, including the
 * phase names. The client renders what the server tells it and holds no exam
 * rules of its own — if the prep minute or the two-minute long turn lived here
 * as well, the two copies would drift and the app would quietly stop matching
 * the real test.
 */

/** Where the exam currently is. Mirrors `core.interview.Phase`. */
export type InterviewPhase =
  | 'greeting'
  | 'part1'
  | 'part2_cue'
  | 'part2_prep'
  | 'part2_speaking'
  | 'part2_followup'
  | 'part3'
  | 'scoring'
  | 'complete';

/** What the client should do next. Mirrors `core.interview.ActionKind`. */
export type InterviewActionKind =
  | 'ask'
  | 'say'
  | 'prepare'
  | 'long_turn'
  | 'finish';

export interface InterviewAction {
  kind: InterviewActionKind;
  phase: InterviewPhase;
  text: string;
  /** Present on timed phases. The server decides; the client only counts down. */
  durationSeconds: number | null;
  /** Cue card bullet points. Part 2 only. */
  bullets: string[];
}

export interface InterviewProgress {
  phase: InterviewPhase;
  phaseIndex: number;
  phaseCount: number;
  questionIndex: number;
  answered: number;
}

export interface InterviewSession {
  id: string;
  phase: InterviewPhase;
  action: InterviewAction;
  progress: InterviewProgress;
  isComplete: boolean;
  speakingAttemptId: string | null;
}

/**
 * Where a transcript came from. Sent with every answer so a poor band can be
 * traced to a poor transcription rather than blamed on the scorer.
 */
export type TranscriptSource =
  | 'android-device'
  | 'server-stt'
  | 'typed'
  | 'unknown';

export interface InterviewAnswer {
  text: string;
  source: TranscriptSource;
}

/** Credentials for the real-time room. Only issued when LiveKit is configured. */
export interface RealtimeToken {
  url: string;
  token: string;
  room: string;
  identity: string;
  expiresAt: number;
}
