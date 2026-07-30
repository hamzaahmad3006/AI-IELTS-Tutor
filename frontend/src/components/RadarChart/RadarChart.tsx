/**
 * Four-module radar (spider) chart on the IELTS 0–9 band scale.
 *
 * Shows shape at a glance: a lopsided polygon says "your Listening carries you
 * and your Writing drags you down" faster than four numbers do.
 */

import React from 'react';
import { View } from 'react-native';
import Svg, { Circle, G, Line, Polygon, Text as SvgText } from 'react-native-svg';
import { useTheme } from '../theme/useTheme';
import { FONT_SIZE } from '../../constants';

export interface RadarAxis {
  label: string;
  /** Null renders the axis at the centre — no data, not a zero score. */
  value: number | null;
}

interface RadarChartProps {
  axes: RadarAxis[];
  size?: number;
  maxBand?: number;
  /** Polygon stroke/fill. Defaults to the theme primary. */
  color?: string;
  testID?: string;
}

/** Fraction of the radius reserved for axis labels. */
const LABEL_INSET = 0.78;
const RINGS = [1 / 3, 2 / 3, 1] as const;

/**
 * Radius fraction for a band: 0 for an unmeasured axis, otherwise clamped into
 * 0..1 so a corrupt band can never draw outside the chart.
 *
 * Exported because SVG text is not queryable in the test renderer, so this and
 * `axisCaption` are unit-tested directly rather than scraped off the tree.
 */
export const bandFraction = (value: number | null, maxBand = 9): number =>
  value === null ? 0 : Math.max(0, Math.min(1, value / (maxBand || 1)));

/** Bare label when unmeasured, so a missing band never reads as a score of 0. */
export const axisCaption = (axis: RadarAxis): string =>
  axis.value === null ? axis.label : `${axis.label} ${axis.value}`;

export const RadarChart: React.FC<RadarChartProps> = ({
  axes,
  size = 220,
  maxBand = 9,
  color,
  testID,
}) => {
  const theme = useTheme();
  const stroke = color ?? theme.colors.primary;

  const centre = size / 2;
  const radius = centre * LABEL_INSET;
  const count = axes.length;

  // Start at 12 o'clock and go clockwise, which is how these are read.
  const angleFor = (index: number): number =>
    -Math.PI / 2 + (index * 2 * Math.PI) / Math.max(1, count);

  const pointAt = (index: number, fraction: number): [number, number] => {
    const angle = angleFor(index);
    return [
      centre + radius * fraction * Math.cos(angle),
      centre + radius * fraction * Math.sin(angle),
    ];
  };

  const polygon = axes
    .map((axis, i) => pointAt(i, bandFraction(axis.value, maxBand)).join(','))
    .join(' ');

  const hasAnyValue = axes.some((axis) => axis.value !== null);

  return (
    <View testID={testID}>
      <Svg width={size} height={size}>
        {/* Concentric guide rings */}
        {RINGS.map((ring) => (
          <Polygon
            key={`ring-${ring}`}
            points={axes.map((_, i) => pointAt(i, ring).join(',')).join(' ')}
            fill="none"
            stroke={theme.colors.outlineVariant}
            strokeWidth={1}
          />
        ))}

        {/* Spokes */}
        {axes.map((axis, i) => {
          const [x, y] = pointAt(i, 1);
          return (
            <Line
              key={`spoke-${axis.label}`}
              x1={centre}
              y1={centre}
              x2={x}
              y2={y}
              stroke={theme.colors.outlineVariant}
              strokeWidth={1}
            />
          );
        })}

        {hasAnyValue && (
          <G>
            <Polygon
              points={polygon}
              fill={stroke}
              fillOpacity={0.18}
              stroke={stroke}
              strokeWidth={2}
              strokeLinejoin="round"
            />
            {axes.map((axis, i) => {
              if (axis.value === null) {
                return null;
              }
              const [x, y] = pointAt(i, bandFraction(axis.value, maxBand));
              return (
                <Circle
                  key={`dot-${axis.label}`}
                  cx={x}
                  cy={y}
                  r={3.5}
                  fill={stroke}
                />
              );
            })}
          </G>
        )}

        {/* Axis labels, nudged outside the outer ring */}
        {axes.map((axis, i) => {
          const [x, y] = pointAt(i, 1.16);
          const angle = angleFor(i);
          const cos = Math.cos(angle);
          const anchor =
            Math.abs(cos) < 0.3 ? 'middle' : cos > 0 ? 'start' : 'end';
          return (
            <SvgText
              key={`label-${axis.label}`}
              x={x}
              y={y + 4}
              fill={theme.colors.onSurfaceVariant}
              fontSize={FONT_SIZE.xs}
              textAnchor={anchor}
            >
              {axisCaption(axis)}
            </SvgText>
          );
        })}
      </Svg>
    </View>
  );
};
