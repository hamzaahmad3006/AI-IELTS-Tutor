/** Analytics API module (progress, band trend + prediction). */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import {
  MOCK_INSIGHTS,
  MOCK_PREDICTION,
  MOCK_PROGRESS,
  MOCK_TREND,
} from '@fixtures';
import type {
  InsightsResponse,
  PredictionResponse,
  ProgressResponse,
  TrendResponse,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

export const analyticsApi = {
  async getProgress(): Promise<ProgressResponse> {
    if (API_CONFIG.useMock) {
      await delay(400);
      return MOCK_PROGRESS;
    }
    try {
      const { data } = await apiClient.get<ProgressResponse>(
        ENDPOINTS.analytics.progress,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getTrend(): Promise<TrendResponse> {
    if (API_CONFIG.useMock) {
      await delay(400);
      return MOCK_TREND;
    }
    try {
      const { data } = await apiClient.get<TrendResponse>(
        ENDPOINTS.analytics.trend,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getInsights(): Promise<InsightsResponse> {
    if (API_CONFIG.useMock) {
      await delay(400);
      return MOCK_INSIGHTS;
    }
    try {
      const { data } = await apiClient.get<InsightsResponse>(
        ENDPOINTS.analytics.insights,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getPrediction(): Promise<PredictionResponse> {
    if (API_CONFIG.useMock) {
      await delay(400);
      return MOCK_PREDICTION;
    }
    try {
      const { data } = await apiClient.get<PredictionResponse>(
        ENDPOINTS.analytics.prediction,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
