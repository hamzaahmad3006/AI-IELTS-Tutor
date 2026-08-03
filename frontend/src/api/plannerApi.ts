/** Study planner API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_STUDY_PLAN } from './mock/fixtures';
import type { PlanTask, StudyPlan } from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

export const plannerApi = {
  /** Null when the learner has no plan yet — distinct from an empty plan. */
  async getPlan(): Promise<StudyPlan | null> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_STUDY_PLAN;
    }
    try {
      const { data } = await apiClient.get<StudyPlan>(ENDPOINTS.planner.plan);
      return data;
    } catch (error) {
      const problem = toApiProblem(error);
      if (problem.status === 404) {
        return null;
      }
      throw problem;
    }
  },

  async generate(): Promise<StudyPlan> {
    if (API_CONFIG.useMock) {
      await delay(500);
      return MOCK_STUDY_PLAN;
    }
    try {
      const { data } = await apiClient.post<StudyPlan>(ENDPOINTS.planner.plan);
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async setTaskDone(taskId: string, isDone: boolean): Promise<PlanTask> {
    if (API_CONFIG.useMock) {
      await delay(200);
      const task = MOCK_STUDY_PLAN.tasks[0];
      return { ...task, isDone };
    }
    try {
      const { data } = await apiClient.patch<PlanTask>(
        `${ENDPOINTS.planner.tasks}/${taskId}`,
        { isDone },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
