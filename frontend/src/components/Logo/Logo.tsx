/** AURAGRAPH brand mark: indigo speech bubble containing an ascending bar graph. */

import React from 'react';
import Svg, { Path, Rect } from 'react-native-svg';
import { PALETTE } from '@constants';

interface LogoProps {
  size?: number;
  bubbleColor?: string;
  markColor?: string;
}

export const Logo: React.FC<LogoProps> = ({
  size = 64,
  bubbleColor = PALETTE.indigo,
  markColor = PALETTE.white,
}) => (
  <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
    {/* Speech bubble */}
    <Path
      d="M50 8C26 8 8 24 8 45c0 12 6 22 16 29l-3 14 16-8c5 1 10 2 13 2 24 0 42-16 42-37S74 8 50 8Z"
      fill={bubbleColor}
    />
    {/* Ascending bars */}
    <Rect x="28" y="52" width="8" height="16" rx="2" fill={markColor} />
    <Rect x="41" y="42" width="8" height="26" rx="2" fill={markColor} />
    <Rect x="54" y="34" width="8" height="34" rx="2" fill={markColor} />
    <Rect x="67" y="26" width="8" height="42" rx="2" fill={markColor} />
    {/* Trend line */}
    <Path
      d="M28 50l12-8 13-6 14-10"
      stroke={markColor}
      strokeWidth="3.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </Svg>
);
