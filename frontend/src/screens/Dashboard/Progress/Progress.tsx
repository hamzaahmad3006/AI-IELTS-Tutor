/** Progress/analytics (UI only). */

import React from 'react';
import { ComingSoon } from '../../../components';
import { useProgress } from './useProgress';

export const Progress: React.FC = () => {
  const { title, subtitle, icon } = useProgress();
  return <ComingSoon title={title} subtitle={subtitle} icon={icon} />;
};
