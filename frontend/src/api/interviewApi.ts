/** Spoken interview API module. */

import { apiClient, toApiProblem } from './client';
import { ENDPOINTS } from './endpoints';
import type {
  InterviewAnswer,
  InterviewSession,
  RealtimeToken,
  SpeakingResult,
} from '../types';

/**
 * No mock branch, unlike the other modules.
 *
 * A fixture would have to fake the whole examiner state machine — phase
 * ordering, the prep countdown, the two-minute cap — and a second
 * implementation of the exam rules is exactly what this design avoids. The
 * interview needs the real backend, which is also what it will always have:
 * unlike a passage or a cue card, there is nothing here to preview offline.
 */
export const interviewApi = {
  async start(difficulty?: string): Promise<InterviewSession> {
    try {
      const { data } = await apiClient.post<InterviewSession>(
        ENDPOINTS.interview.sessions,
        null,
        { params: difficulty ? { difficulty } : undefined },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /**
   * Re-read the current instruction without advancing.
   *
   * Safe to call repeatedly, which is what makes recovery possible: a client
   * that dropped mid-question asks again rather than skipping ahead.
   */
  async get(sessionId: string): Promise<InterviewSession> {
    try {
      const { data } = await apiClient.get<InterviewSession>(
        ENDPOINTS.interview.session(sessionId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async answer(
    sessionId: string,
    payload: InterviewAnswer,
  ): Promise<InterviewSession> {
    try {
      const { data } = await apiClient.post<InterviewSession>(
        ENDPOINTS.interview.answer(sessionId),
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /** Upload a recording; the server transcribes it and advances the exam. */
  async answerWithAudio(
    sessionId: string,
    file: { uri: string; name: string; type: string },
  ): Promise<InterviewSession> {
    const form = new FormData();
    // React Native's FormData takes this shape for files; it is not a Blob and
    // TypeScript's DOM lib does not describe it, hence the cast.
    form.append('audio', file as unknown as Blob);

    try {
      const { data } = await apiClient.post<InterviewSession>(
        ENDPOINTS.interview.answerAudio(sessionId),
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

  /** Start the long turn before the preparation minute is up. */
  async skipPreparation(sessionId: string): Promise<InterviewSession> {
    try {
      const { data } = await apiClient.post<InterviewSession>(
        ENDPOINTS.interview.skipPrep(sessionId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async score(sessionId: string): Promise<SpeakingResult> {
    try {
      const { data } = await apiClient.post<SpeakingResult>(
        ENDPOINTS.interview.score(sessionId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /**
   * Credentials for the real-time room.
   *
   * Returns 503 when LiveKit is not configured, which is a normal state rather
   * than an error: the upload-based path still works, so callers should fall
   * back rather than surface a failure.
   */
  async realtimeToken(sessionId: string): Promise<RealtimeToken> {
    try {
      const { data } = await apiClient.post<RealtimeToken>(
        ENDPOINTS.interview.rtcToken(sessionId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
