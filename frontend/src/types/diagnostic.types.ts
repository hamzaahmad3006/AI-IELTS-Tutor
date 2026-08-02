/** Placement diagnostic types (mirror `/diagnostic`). */

import type { Band } from './common.types';

export interface DiagnosticQuestion {
  id: string;
  type: string;
  prompt: string;
  options: string[] | null;
}

export interface DiagnosticReading {
  passageId: string;
  title: string;
  body: string;
  questions: DiagnosticQuestion[];
}

export interface DiagnosticListening {
  clipId: string;
  title: string;
  audioUrl: string;
  durationSec: number;
  questions: DiagnosticQuestion[];
}

export interface DiagnosticWriting {
  promptId: string;
  prompt: string;
  minWords: number;
}

export interface DiagnosticSpeaking {
  prompt: string;
  minWords: number;
}

export interface DiagnosticSet {
  reading: DiagnosticReading;
  listening: DiagnosticListening;
  writing: DiagnosticWriting;
  speaking: DiagnosticSpeaking;
  note: string;
}

export interface DiagnosticSubmission {
  readingAnswers: Record<string, string>;
  listeningAnswers: Record<string, string>;
  /** Null means not attempted — the API reports no estimate rather than zero. */
  writingText: string | null;
  speakingText: string | null;
}

export interface ModuleBaseline {
  module: string;
  band: Band | null;
  detail: string;
}

export interface DiagnosticResult {
  baselines: ModuleBaseline[];
  overallBand: Band | null;
  cefrLevel: string | null;
  cefrDescription: string;
  summary: string;
}
