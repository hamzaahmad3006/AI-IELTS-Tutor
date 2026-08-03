/**
 * SVG icon component. Maps a typed IconName to 24x24 vector path data so the
 * app has no dependency on native icon fonts.
 */

import React from 'react';
import Svg, { Path, Circle, Line, Polyline, Rect } from 'react-native-svg';
import type { IconName } from '@constants';
import { useTheme } from '../theme/useTheme';
import type { ThemeColors } from '@constants';

interface IconProps {
  name: IconName;
  size?: number;
  color?: keyof ThemeColors;
  /** Raw color string that takes precedence over the themed `color` token. */
  overrideColor?: string;
  strokeWidth?: number;
}

const PATHS: Record<IconName, string> = {
  home: 'M3 10.5 12 3l9 7.5M5 9.5V21h14V9.5',
  practice: 'M6.5 6.5 3 10l3.5 3.5M17.5 6.5 21 10l-3.5 3.5M13.5 4l-3 16',
  progress: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  coach: 'M4 5h16v11H8l-4 4V5Z',
  profile: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 21c0-4 4-6 8-6s8 2 8 6',
  speaking:
    'M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3ZM5 11a7 7 0 0 0 14 0M12 18v3',
  writing: 'M4 20h16M6 16l9-9 3 3-9 9H6v-3Z',
  reading:
    'M12 6c-2-1.5-5-1.5-8 0v12c3-1.5 6-1.5 8 0 2-1.5 5-1.5 8 0V6c-3-1.5-6-1.5-8 0Zm0 0v12',
  listening:
    'M4 13v-1a8 8 0 0 1 16 0v1M4 13a2 2 0 0 0 2 2h1v-5H6a2 2 0 0 0-2 2Zm16 0a2 2 0 0 1-2 2h-1v-5h1a2 2 0 0 1 2 2Z',
  back: 'M15 5l-7 7 7 7',
  'arrow-right': 'M5 12h14M13 6l6 6-6 6',
  bell: 'M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6M10 20a2 2 0 0 0 4 0',
  mic: 'M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3ZM5 11a7 7 0 0 0 14 0M12 18v3',
  pause: 'M9 5v14M15 5v14',
  play: 'M7 4v16l13-8L7 4Z',
  'end-call': 'M3 10c5-4 13-4 18 0l-2 3-4-1v-2c-2-1-4-1-6 0v2l-4 1-2-3Z',
  check: 'M5 12l5 5 9-11',
  timer: 'M12 8v5l3 2M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM9 2h6',
  rocket:
    'M5 15c-1 2-1 4-1 4s2 0 4-1M9 15l-3-3 4-6c2-3 5-4 8-4 0 3-1 6-4 8l-6 4-3-3Z',
  export: 'M12 15V4M8 8l4-4 4 4M5 15v4h14v-4',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 11v5M12 8h.01',
  translate:
    'M3 5h9M7 4v1M9 5c0 5-4 8-6 8M5 9c0 2 3 4 6 4M14 20l4-9 4 9M15.5 17h5',
  edit: 'M4 20h16M6 16l9-9 3 3-9 9H6v-3Z',
  sparkle: 'M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2 2-6Z',
  flame: 'M12 3s5 4 5 9a5 5 0 0 1-10 0c0-2 1-3 1-3s3 1 4-6Z',
};

export const Icon: React.FC<IconProps> = ({
  name,
  size = 24,
  color = 'textPrimary',
  overrideColor,
  strokeWidth = 2,
}) => {
  const theme = useTheme();
  const stroke = overrideColor ?? theme.colors[color];
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d={PATHS[name]}
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
};

// Re-export svg primitives for screens that need custom vector art.
export { Svg, Path, Circle, Line, Polyline, Rect };
