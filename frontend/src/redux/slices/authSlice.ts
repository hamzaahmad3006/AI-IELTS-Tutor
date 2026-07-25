/** Authentication slice with async login/register thunks. */

import {
  createAsyncThunk,
  createSlice,
  type PayloadAction,
} from '@reduxjs/toolkit';
import { authApi } from '../../api';
import type {
  AuthResponse,
  AuthState,
  ApiProblem,
  LoginRequest,
  RegisterRequest,
} from '../../types';

const initialState: AuthState = {
  user: null,
  tokens: null,
  isAuthenticated: false,
  isBootstrapping: false,
  error: null,
};

export const loginThunk = createAsyncThunk<
  AuthResponse,
  LoginRequest,
  { rejectValue: string }
>('auth/login', async (payload, { rejectWithValue }) => {
  try {
    return await authApi.login(payload);
  } catch (error) {
    return rejectWithValue((error as ApiProblem).title);
  }
});

export const registerThunk = createAsyncThunk<
  AuthResponse,
  RegisterRequest,
  { rejectValue: string }
>('auth/register', async (payload, { rejectWithValue }) => {
  try {
    return await authApi.register(payload);
  } catch (error) {
    return rejectWithValue((error as ApiProblem).title);
  }
});

/** Rotate tokens using the stored refresh token. */
export const refreshThunk = createAsyncThunk<
  AuthResponse,
  string,
  { rejectValue: string }
>('auth/refresh', async (refreshToken, { rejectWithValue }) => {
  try {
    return await authApi.refresh(refreshToken);
  } catch (error) {
    return rejectWithValue((error as ApiProblem).title);
  }
});

/** Revoke the refresh token server-side, then clear local state. */
export const logoutThunk = createAsyncThunk<void, string | undefined>(
  'auth/logoutServer',
  async (refreshToken) => {
    if (refreshToken) {
      await authApi.logout(refreshToken);
    }
  },
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout(state): void {
      state.user = null;
      state.tokens = null;
      state.isAuthenticated = false;
      state.error = null;
    },
    clearAuthError(state): void {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    const onFulfilled = (
      state: AuthState,
      action: PayloadAction<AuthResponse>,
    ): void => {
      state.user = action.payload.user;
      state.tokens = action.payload.tokens;
      state.isAuthenticated = true;
      state.isBootstrapping = false;
      state.error = null;
    };

    builder
      .addCase(loginThunk.pending, (state) => {
        state.isBootstrapping = true;
        state.error = null;
      })
      .addCase(loginThunk.fulfilled, onFulfilled)
      .addCase(loginThunk.rejected, (state, action) => {
        state.isBootstrapping = false;
        state.error = action.payload ?? 'Login failed';
      })
      .addCase(registerThunk.pending, (state) => {
        state.isBootstrapping = true;
        state.error = null;
      })
      .addCase(registerThunk.fulfilled, onFulfilled)
      .addCase(registerThunk.rejected, (state, action) => {
        state.isBootstrapping = false;
        state.error = action.payload ?? 'Registration failed';
      })
      // Refresh updates the token pair without touching auth status.
      .addCase(refreshThunk.fulfilled, (state, action) => {
        state.user = action.payload.user;
        state.tokens = action.payload.tokens;
        state.isAuthenticated = true;
      })
      .addCase(refreshThunk.rejected, (state) => {
        // Refresh failed -> force a clean sign-out.
        state.user = null;
        state.tokens = null;
        state.isAuthenticated = false;
      })
      // Server logout: clear local session regardless of the call's outcome.
      .addCase(logoutThunk.fulfilled, (state) => {
        state.user = null;
        state.tokens = null;
        state.isAuthenticated = false;
        state.error = null;
      });
  },
});

export const { logout, clearAuthError } = authSlice.actions;
export const authReducer = authSlice.reducer;
