/** Redux store: combines reducers, wires redux-persist for auth + theme. */

import { combineReducers, configureStore } from '@reduxjs/toolkit';
import {
  persistReducer,
  persistStore,
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
} from 'redux-persist';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { secureStorage } from '../storage/secureStorage';
import { authReducer } from './slices/authSlice';
import { onboardingReducer } from './slices/onboardingSlice';
import { dashboardReducer } from './slices/dashboardSlice';
import { themeReducer } from './slices/themeSlice';
import { toastReducer } from './slices/toastSlice';
import { offlineReducer } from './slices/offlineSlice';

/**
 * Credentials go to the Keystore; everything else stays in AsyncStorage.
 *
 * Nested rather than moving the whole store, for two reasons. Keystore writes
 * are far slower than a file write, and the offline queue is written on every
 * queued mutation -- routing that through hardware-backed crypto would add
 * latency to an operation that happens constantly and holds nothing secret.
 * And a Keystore failure only costs the session, instead of also discarding
 * queued work and the user's theme.
 */
const authPersistConfig = {
  key: 'auth',
  storage: secureStorage,
};

const rootReducer = combineReducers({
  auth: persistReducer(authPersistConfig, authReducer),
  onboarding: onboardingReducer,
  dashboard: dashboardReducer,
  theme: themeReducer,
  toast: toastReducer,
  offline: offlineReducer,
});

const persistConfig = {
  key: 'root',
  storage: AsyncStorage,
  // `offline` is persisted because a queue that empties on restart would
  // silently discard the very work it exists to protect.
  //
  // `auth` is deliberately absent: it has its own nested persistor above,
  // writing to the Keystore. Listing it here as well would write a second,
  // plaintext copy to AsyncStorage and defeat the whole exercise.
  whitelist: ['theme', 'offline'],
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: getDefaultMiddleware =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }),
});

export const persistor = persistStore(store);

export type RootState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;
