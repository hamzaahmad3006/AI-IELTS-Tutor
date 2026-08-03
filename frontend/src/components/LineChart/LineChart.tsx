/**
 * Band trend line chart (SVG).
 *
 * Plots one or more series on the fixed IELTS 0–9 band scale rather than
 * auto-scaling to the data: a learner comparing two screenshots needs the same
 * y-axis both times, and an auto-scaled axis would make a 6.0→6.5 nudge look
 * like a leap.
 */

import React from 'react';
import { View } from 'react-native';
import Svg, { Circle, G, Line, Path, Text as SvgText } from 'react-native-svg';
import { AppText } from '../AppText/AppText';
import { useTheme } from '../theme/useTheme';
import { FONT_SIZE, SPACING } from '@constants';

export interface LineSeries {
  label: string;
  color: string;
  /** Oldest first. Fewer than two points renders as a single dot. */
  values: number[];
}

interface LineChartProps {
  series: LineSeries[];
  height?: number;
  /** Y-axis bounds. Defaults to the full IELTS band scale. */
  minBand?: number;
  maxBand?: number;
  /** Hide the colour key when the caller renders its own. */
  showLegend?: boolean;
  testID?: string;
}

const PADDING = { top: 12, right: 12, bottom: 8, left: 30 } as const;
const GRID_BANDS = [0, 3, 6, 9] as const;

export const LineChart: React.FC<LineChartProps> = ({
  series,
  height = 180,
  minBand = 0,
  maxBand = 9,
  showLegend = true,
  testID,
}) => {
  const theme = useTheme();
  const [width, setWidth] = React.useState<number>(0);

  const plotWidth = Math.max(0, width - PADDING.left - PADDING.right);
  const plotHeight = Math.max(0, height - PADDING.top - PADDING.bottom);
  const span = maxBand - minBand || 1;

  const yFor = (band: number): number =>
    PADDING.top + plotHeight * (1 - (band - minBand) / span);

  /** Evenly spaced along x: the axis is attempt order, not wall-clock time. */
  const xFor = (index: number, count: number): number =>
    PADDING.left +
    (count <= 1 ? plotWidth / 2 : (plotWidth * index) / (count - 1));

  const drawn = series.filter(s => s.values.length > 0);
  const hasData = drawn.length > 0;

  return (
    <View testID={testID}>
      <View
        onLayout={event => setWidth(event.nativeEvent.layout.width)}
        style={{ height }}
      >
        {width > 0 && (
          <Svg width={width} height={height}>
            {/* Gridlines + band labels */}
            {GRID_BANDS.filter(b => b >= minBand && b <= maxBand).map(band => (
              <G key={`grid-${band}`}>
                <Line
                  x1={PADDING.left}
                  y1={yFor(band)}
                  x2={PADDING.left + plotWidth}
                  y2={yFor(band)}
                  stroke={theme.colors.outlineVariant}
                  strokeWidth={1}
                />
                <SvgText
                  x={PADDING.left - 6}
                  y={yFor(band) + 4}
                  fill={theme.colors.onSurfaceVariant}
                  fontSize={FONT_SIZE.xs}
                  textAnchor="end"
                >
                  {String(band)}
                </SvgText>
              </G>
            ))}

            {drawn.map(s => {
              const count = s.values.length;
              const path = s.values
                .map(
                  (band, i) =>
                    `${i === 0 ? 'M' : 'L'}${xFor(i, count)},${yFor(band)}`,
                )
                .join(' ');
              return (
                <G key={s.label}>
                  {count > 1 && (
                    <Path
                      d={path}
                      stroke={s.color}
                      strokeWidth={2.5}
                      fill="none"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  )}
                  {s.values.map((band, i) => (
                    <Circle
                      key={`${s.label}-${i}`}
                      cx={xFor(i, count)}
                      cy={yFor(band)}
                      r={3.5}
                      fill={s.color}
                    />
                  ))}
                </G>
              );
            })}
          </Svg>
        )}
      </View>

      {!hasData && (
        <AppText variant="labelSm" color="onSurfaceVariant">
          No scored attempts yet — complete a practice to start your trend.
        </AppText>
      )}

      {showLegend && hasData && (
        <View
          style={{
            flexDirection: 'row',
            flexWrap: 'wrap',
            gap: SPACING.md,
            marginTop: SPACING.sm,
          }}
        >
          {drawn.map(s => (
            <View
              key={s.label}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}
            >
              <View
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 5,
                  backgroundColor: s.color,
                }}
              />
              <AppText variant="labelSm" color="onSurfaceVariant">
                {s.label}
              </AppText>
            </View>
          ))}
        </View>
      )}
    </View>
  );
};
