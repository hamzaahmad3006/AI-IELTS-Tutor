/** Study planner types (mirror `/planner`). */

import type { Band, IeltsModule } from './common.types';

export interface PlanTask {
  id: string;
  week: number;
  module: IeltsModule;
  title: string;
  detail: string;
  minutes: number;
  priority: number;
  isDone: boolean;
}

export interface StudyPlan {
  id: string;
  targetBand: Band;
  examDate: string | null;
  dailyMinutes: number;
  weeks: number;
  rationale: string;
  tasks: PlanTask[];
  completedCount: number;
  totalCount: number;
}
