/** Daily coach (UI only). */

import React from 'react';
import { ComingSoon } from '../../../components';
import { useCoach } from './useCoach';

export const Coach: React.FC = () => {
  const { title, subtitle, icon } = useCoach();
  return <ComingSoon title={title} subtitle={subtitle} icon={icon} />;
};
