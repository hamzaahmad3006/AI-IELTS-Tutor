/** Practice hub screen logic (placeholder milestone). */

import type { IconName } from '../../../constants';

interface UsePracticeResult {
  title: string;
  subtitle: string;
  icon: IconName;
}

export const usePractice = (): UsePracticeResult => ({
  title: 'Practice Hub',
  subtitle: 'Reading, Listening, Writing and Speaking practice arrive here next.',
  icon: 'practice',
});
