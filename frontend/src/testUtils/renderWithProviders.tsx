/**
 * Test helper: render a screen inside the providers it needs at runtime
 * (Redux store, navigation container, safe-area metrics).
 */

import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { Provider } from 'react-redux';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { render, type RenderResult } from '@testing-library/react-native';
import { store } from '../redux';

const SAFE_AREA_METRICS = {
  frame: { x: 0, y: 0, width: 390, height: 844 },
  insets: { top: 47, left: 0, right: 0, bottom: 34 },
};

export const renderWithProviders = (ui: React.ReactElement): RenderResult =>
  render(
    <Provider store={store}>
      <SafeAreaProvider initialMetrics={SAFE_AREA_METRICS}>
        <NavigationContainer>{ui}</NavigationContainer>
      </SafeAreaProvider>
    </Provider>,
  );
