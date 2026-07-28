/** Vocabulary (spaced repetition) API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import type {
  VocabGrade,
  VocabGradeResult,
  VocabQueue,
  VocabStats,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

const MOCK_QUEUE: VocabQueue = {
  items: [
    {
      itemId: 'v1',
      word: 'detrimental',
      definition: 'Tending to cause harm or damage.',
      example: 'Excessive screen time can be detrimental to sleep quality.',
      lexicalField: 'environment',
      cefrLevel: 'C1',
      isNew: true,
    },
    {
      itemId: 'v2',
      word: 'mitigate',
      definition: 'To make something bad less severe or serious.',
      example: 'Planting trees helps mitigate the effects of urban heat.',
      lexicalField: 'environment',
      cefrLevel: 'C1',
      isNew: true,
    },
    {
      itemId: 'v3',
      word: 'prevalent',
      definition: 'Widespread in a particular area or at a particular time.',
      example: 'Remote work has become prevalent in many industries.',
      lexicalField: 'society',
      cefrLevel: 'B2',
      isNew: true,
    },
  ],
  dueCount: 0,
  newCount: 3,
};

const MOCK_STATS: VocabStats = {
  totalItems: 8,
  started: 0,
  dueNow: 0,
  mastered: 0,
};

export const vocabularyApi = {
  async getQueue(limit = 10): Promise<VocabQueue> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_QUEUE;
    }
    try {
      const { data } = await apiClient.get<VocabQueue>(
        ENDPOINTS.vocabulary.review,
        { params: { limit } },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async grade(itemId: string, grade: VocabGrade): Promise<VocabGradeResult> {
    if (API_CONFIG.useMock) {
      await delay(200);
      return {
        itemId,
        repetitions: 1,
        intervalDays: 1,
        easeFactor: 2.5,
        dueAt: new Date(Date.now() + 86400000).toISOString(),
        totalReviews: 1,
      };
    }
    try {
      const { data } = await apiClient.post<VocabGradeResult>(
        ENDPOINTS.vocabulary.grade,
        { itemId, grade },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getStats(): Promise<VocabStats> {
    if (API_CONFIG.useMock) {
      await delay(200);
      return MOCK_STATS;
    }
    try {
      const { data } = await apiClient.get<VocabStats>(
        ENDPOINTS.vocabulary.stats,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
