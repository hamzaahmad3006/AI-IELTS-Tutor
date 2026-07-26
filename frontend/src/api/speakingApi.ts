/** Speaking API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_SPEAKING_RESULT, MOCK_SPEAKING_SESSION } from './mock/fixtures';
import type {
  CueCard,
  SpeakingHistoryPage,
  SpeakingResult,
  SpeakingSession,
  SpeakingSubmit,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

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
      const { data } = await apiClient.get<CueCard>(ENDPOINTS.speaking.cueCards, {
        params: difficulty ? { difficulty } : undefined,
      });
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /** Submit an interview transcript for AI scoring. */
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
