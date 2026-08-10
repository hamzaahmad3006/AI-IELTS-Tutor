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
import {
  coachReducer,
  insightsReducer,
  plannerReducer,
  progressReducer,
  trendReducer,
  vocabularyReducer,
  weaknessReducer,
} from './slices/contentSlices';

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
  // Cached server reads. Not persisted: they are copies of data the server
  // owns, and a stale cache survived across a restart is worse than a fetch.
  progress: progressReducer,
  trend: trendReducer,
  insights: insightsReducer,
  planner: plannerReducer,
  vocabulary: vocabularyReducer,
  weakness: weaknessReducer,
  coach: coachReducer,
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

type RootReducerState = ReturnType<typeof rootReducer>;

/**
 * Wraps the root reducer so logging out clears every cached read.
 *
 * Done here rather than by dispatching a reset per slice, because a
 * hand-written list of slices to clear is one someone forgets to update — and
 * the thing it forgets is one learner's progress still on screen for the next
 * person to sign in on the same device. Discarding the whole state and letting
 * every reducer rebuild its initial value cannot be forgotten.
 *
 * `theme` survives, deliberately. It is a device preference rather than
 * anyone's data, and resetting it to light mode at 11pm because someone signed
 * out is a small hostility.
 */
const clearOnLogout = (
  state: RootReducerState | undefined,
  action: { type: string },
): RootReducerState => {
  if (
    action.type === 'auth/logout' ||
    action.type === 'auth/logoutServer/fulfilled'
  ) {
    return rootReducer(
      { theme: state?.theme } as Partial<RootReducerState> as RootReducerState,
      action,
    );
  }
  return rootReducer(state, action);
};

const persistedReducer = persistReducer(persistConfig, clearOnLogout);

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
