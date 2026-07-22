/** Daily coach screen logic (placeholder milestone). */

import type { IconName } from '../../../constants';

interface UseCoachResult {
  title: string;
  subtitle: string;
  icon: IconName;
}

export const useCoach = (): UseCoachResult => ({
  title: 'Daily AI Coach',
  subtitle: 'Personalized recommendations and motivation, tailored to your weaknesses.',
  icon: 'coach',
});
