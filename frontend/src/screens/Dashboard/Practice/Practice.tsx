/** Practice hub (UI only). */

import React from 'react';
import { ComingSoon } from '../../../components';
import { usePractice } from './usePractice';

export const Practice: React.FC = () => {
  const { title, subtitle, icon } = usePractice();
  return <ComingSoon title={title} subtitle={subtitle} icon={icon} />;
};
