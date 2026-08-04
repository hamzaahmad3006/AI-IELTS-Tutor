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
import { authReducer } from './slices/authSlice';
import { onboardingReducer } from './slices/onboardingSlice';
import { dashboardReducer } from './slices/dashboardSlice';
import { themeReducer } from './slices/themeSlice';
import { toastReducer } from './slices/toastSlice';
import { offlineReducer } from './slices/offlineSlice';

const rootReducer = combineReducers({
  auth: authReducer,
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
  whitelist: ['auth', 'theme', 'offline'],
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
