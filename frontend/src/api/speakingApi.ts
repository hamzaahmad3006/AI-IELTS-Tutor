/** Speaking API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import {
  MOCK_SPEAKING_RESULT,
  MOCK_SPEAKING_SESSION,
  MOCK_SPEAKING_QUESTIONS,
} from '@fixtures';
import type {
  SpeakingPart,
  SpeakingQuestionSet,
  CueCard,
  SpeakingHistoryPage,
  SpeakingResult,
  SpeakingSession,
  SpeakingSubmit,
  Transcription,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

const MOCK_CUE_CARD: CueCard = {
  id: 'cc_mock_1',
  topic: 'A memorable place',
  prompt: 'Describe a place you visited that made a lasting impression.',
  bulletPoints: [
    'where it was',
    'when you went there',
    'what you did there',
    'and explain why it made a lasting impression',
  ],
  difficulty: 'medium',
  prepSeconds: 60,
  speakSeconds: 120,
};

export const speakingApi = {
  /** Fetch a Part 2 cue card from the backend bank. */
  async getCueCard(difficulty?: string): Promise<CueCard> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_CUE_CARD;
    }
    try {
      const { data } = await apiClient.get<CueCard>(
        ENDPOINTS.speaking.cueCards,
        {
          params: difficulty ? { difficulty } : undefined,
        },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /** Submit an interview transcript for AI scoring. */
  async getQuestionSet(
    part: SpeakingPart,
    difficulty?: string,
  ): Promise<SpeakingQuestionSet> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { ...MOCK_SPEAKING_QUESTIONS, part };
    }
    try {
      const { data } = await apiClient.get<SpeakingQuestionSet>(
        ENDPOINTS.speaking.questions,
        { params: difficulty ? { part, difficulty } : { part } },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /**
   * Turn a recorded answer into text.
   *
   * Returns the transcript rather than a score, so the candidate can correct
   * it before submitting. Recognisers mishear proper nouns constantly, and
   * being marked down for the transcriber's error instead of your own is the
   * worst way a practice tool can fail.
   */
  async transcribe(file: {
    uri: string;
    name: string;
    type: string;
  }): Promise<Transcription> {
    if (API_CONFIG.useMock) {
      await delay(600);
      return {
        text: MOCK_SPEAKING_RESULT.transcript,
        durationMs: 42_000,
        provider: 'mock',
        isUsable: true,
      };
    }
    const form = new FormData();
    // React Native's FormData takes this shape for files; it is not a Blob and
    // TypeScript's DOM lib does not describe it, hence the cast.
    form.append('audio', file as unknown as Blob);

    try {
      const { data } = await apiClient.post<Transcription>(
        ENDPOINTS.speaking.transcribe,
        form,
        {
          // Left to the runtime deliberately: axios must set the multipart
          // boundary itself, and hardcoding the header omits it, which makes
          // the server reject an otherwise valid upload.
          headers: { 'Content-Type': 'multipart/form-data' },
        },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async submit(payload: SpeakingSubmit): Promise<SpeakingResult> {
    if (API_CONFIG.useMock) {
      await delay(800);
      return { ...MOCK_SPEAKING_RESULT, part: payload.part ?? null };
    }
    try {
      const { data } = await apiClient.post<SpeakingResult>(
        ENDPOINTS.speaking.attempts,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getResult(attemptId: string): Promise<SpeakingResult> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { ...MOCK_SPEAKING_RESULT, attemptId };
    }
    try {
      const { data } = await apiClient.get<SpeakingResult>(
        ENDPOINTS.speaking.attempt(attemptId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getHistory(cursor?: string): Promise<SpeakingHistoryPage> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { items: [], nextCursor: null };
    }
    try {
      const { data } = await apiClient.get<SpeakingHistoryPage>(
        ENDPOINTS.speaking.history,
        { params: cursor ? { cursor } : undefined },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /**
   * Real-time interview session (LiveKit) — mock-only until the voice pipeline
   * lands. Used by the Speaking interview screen.
   */
  async createSession(): Promise<SpeakingSession> {
    await delay(800);
    return MOCK_SPEAKING_SESSION;
  },
};
