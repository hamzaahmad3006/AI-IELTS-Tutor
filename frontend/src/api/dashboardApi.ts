/** Dashboard API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_DASHBOARD } from '@fixtures';
import type { DashboardData } from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

export const dashboardApi = {
  async getOverview(): Promise<DashboardData> {
    if (API_CONFIG.useMock) {
      await delay(500);
      return MOCK_DASHBOARD;
    }
    try {
      const { data } = await apiClient.get<DashboardData>(
        ENDPOINTS.dashboard.overview,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
