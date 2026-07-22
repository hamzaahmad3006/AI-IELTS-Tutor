/** Progress/analytics screen logic (placeholder milestone). */

import type { IconName } from '../../../constants';

interface UseProgressResult {
  title: string;
  subtitle: string;
  icon: IconName;
}

export const useProgress = (): UseProgressResult => ({
  title: 'Progress & Analytics',
  subtitle: 'Band trends, velocity and your predicted exam-day score land here.',
  icon: 'progress',
});
