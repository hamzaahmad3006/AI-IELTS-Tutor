/**
 * AI IELTS Tutor — application root.
 * Wires Redux (with persistence), navigation, safe-area and gesture handling.
 */

import React from 'react';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { store, persistor, refreshThunk } from './src/redux';
import { setAuthTokenProvider, setRefreshHandler } from './src/api';
import { RootNavigator } from './src/AppNavigation';
import { PALETTE } from './src/constants';

// Bridge the persisted access token into the axios client (no circular import).
setAuthTokenProvider(() => store.getState().auth.tokens?.accessToken ?? null);

// On a 401, the client asks Redux to rotate the refresh token, then retries.
setRefreshHandler(async () => {
  const refreshToken = store.getState().auth.tokens?.refreshToken;
  if (!refreshToken) {
    return null;
  }
  try {
    const result = await store.dispatch(refreshThunk(refreshToken)).unwrap();
    return result.tokens.accessToken;
  } catch {
    return null;
  }
});

const Loading: React.FC = () => (
  <View style={styles.loading}>
    <ActivityIndicator size="large" color={PALETTE.indigo} />
  </View>
);

const App: React.FC = () => (
  <GestureHandlerRootView style={styles.flex}>
    <Provider store={store}>
      <PersistGate loading={<Loading />} persistor={persistor}>
        <SafeAreaProvider>
          <NavigationContainer>
            <RootNavigator />
          </NavigationContainer>
        </SafeAreaProvider>
      </PersistGate>
    </Provider>
  </GestureHandlerRootView>
);

const styles = StyleSheet.create({
  flex: { flex: 1 },
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FAF8FF',
  },
});

export default App;
