/** Placement diagnostic API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_DIAGNOSTIC_RESULT, MOCK_DIAGNOSTIC_SET } from '@fixtures';
import type {
  DiagnosticResult,
  DiagnosticSet,
  DiagnosticSubmission,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

export const diagnosticApi = {
  async getSet(): Promise<DiagnosticSet> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_DIAGNOSTIC_SET;
    }
    try {
      const { data } = await apiClient.get<DiagnosticSet>(
        ENDPOINTS.diagnostic.root,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async submit(payload: DiagnosticSubmission): Promise<DiagnosticResult> {
    if (API_CONFIG.useMock) {
      await delay(400);
      return MOCK_DIAGNOSTIC_RESULT;
    }
    try {
      const { data } = await apiClient.post<DiagnosticResult>(
        ENDPOINTS.diagnostic.root,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
