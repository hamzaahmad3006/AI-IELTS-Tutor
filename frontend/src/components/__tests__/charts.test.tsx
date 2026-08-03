/**
 * Chart component behaviour: geometry maths and the empty/partial-data paths,
 * which are the cases that actually break in the wild.
 */

import React from 'react';
import { screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../testUtils/renderWithProviders';
import { LineChart, type LineSeries } from '../LineChart/LineChart';
import {
  axisCaption,
  bandFraction,
  RadarChart,
  type RadarAxis,
} from '../RadarChart/RadarChart';

describe('LineChart', () => {
  const series: LineSeries[] = [
    { label: 'Overall band', color: '#4F46E5', values: [6, 6.5, 7] },
  ];

  it('renders the legend for a populated series', () => {
    render(<LineChart series={series} testID="chart" />);
    expect(screen.getByTestId('chart')).toBeTruthy();
    expect(screen.getByText('Overall band')).toBeTruthy();
  });

  it('explains itself instead of drawing an empty frame with no data', () => {
    render(<LineChart series={[{ ...series[0], values: [] }]} />);
    expect(screen.getByText(/No scored attempts yet/)).toBeTruthy();
  });

  it('treats an all-empty series list as no data', () => {
    render(<LineChart series={[]} />);
    expect(screen.getByText(/No scored attempts yet/)).toBeTruthy();
  });

  it('does not render the legend when suppressed', () => {
    render(<LineChart series={series} showLegend={false} />);
    expect(screen.queryByText('Overall band')).toBeNull();
  });

  it('survives a single point, where the x-axis has zero span', () => {
    // count - 1 === 0 would divide by zero if the spacing maths were naive.
    render(<LineChart series={[{ ...series[0], values: [7] }]} testID="one" />);
    expect(screen.getByTestId('one')).toBeTruthy();
  });
});

describe('RadarChart', () => {
  const axes: RadarAxis[] = [
    { label: 'Speaking', value: 7.5 },
    { label: 'Writing', value: 6.5 },
    { label: 'Reading', value: 7 },
    { label: 'Listening', value: 7.5 },
  ];

  it('renders every axis', () => {
    render(<RadarChart axes={axes} testID="radar" />);
    expect(screen.getByTestId('radar')).toBeTruthy();
  });

  // The label and geometry logic is asserted directly: react-native-svg emits
  // <RNSVGTSpan /> with no text child in the test renderer, so SVG captions
  // cannot be found via getByText.
  it('captions a measured axis with its band', () => {
    expect(axisCaption({ label: 'Speaking', value: 7.5 })).toBe('Speaking 7.5');
  });

  it('captions an unmeasured axis without a number', () => {
    // A null band means "not measured" and must not read as a score of 0.
    expect(axisCaption({ label: 'Listening', value: null })).toBe('Listening');
  });

  it('collapses an unmeasured axis to the centre', () => {
    expect(bandFraction(null)).toBe(0);
  });

  it('scales a band against the axis maximum', () => {
    expect(bandFraction(9)).toBe(1);
    expect(bandFraction(4.5)).toBe(0.5);
  });

  it('clamps out-of-range bands inside the chart', () => {
    // Defends the drawing code against bad data rather than trusting the API.
    expect(bandFraction(12)).toBe(1);
    expect(bandFraction(-3)).toBe(0);
  });

  it('renders with every axis unmeasured', () => {
    render(
      <RadarChart
        axes={axes.map(a => ({ ...a, value: null }))}
        testID="empty-radar"
      />,
    );
    expect(screen.getByTestId('empty-radar')).toBeTruthy();
  });
});
