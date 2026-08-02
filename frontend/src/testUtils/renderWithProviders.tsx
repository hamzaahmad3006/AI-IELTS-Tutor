/**
 * Test helper: render a screen inside the providers it needs at runtime
 * (Redux store, navigation container, safe-area metrics).
 */

import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Provider } from 'react-redux';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { render, type RenderResult } from '@testing-library/react-native';
import { store } from '../redux';

const SAFE_AREA_METRICS = {
  frame: { x: 0, y: 0, width: 390, height: 844 },
  insets: { top: 47, left: 0, right: 0, bottom: 34 },
};

interface RenderOptions {
  /**
   * Params for screens that call `useRoute`. Supplying these mounts the UI as a
   * real screen inside a navigator, because `useRoute` throws outside one —
   * mocking it instead would let a screen pass its tests while crashing in the
   * app.
   */
  routeParams?: Record<string, unknown>;
}

const Providers: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Provider store={store}>
    <SafeAreaProvider initialMetrics={SAFE_AREA_METRICS}>
      <NavigationContainer>{children}</NavigationContainer>
    </SafeAreaProvider>
  </Provider>
);

const Stack = createNativeStackNavigator();

export const renderWithProviders = (
  ui: React.ReactElement,
  options: RenderOptions = {},
): RenderResult => {
  if (!options.routeParams) {
    return render(<Providers>{ui}</Providers>);
  }

  const Screen = (): React.ReactElement => ui;

  return render(
    <Providers>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen
          name="TestScreen"
          component={Screen}
          initialParams={options.routeParams}
        />
      </Stack.Navigator>
    </Providers>,
  );
};
