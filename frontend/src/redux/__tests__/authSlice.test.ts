import {
  authReducer,
  clearAuthError,
  loginThunk,
  logout,
  logoutThunk,
  refreshThunk,
} from '../slices/authSlice';
import type { AuthResponse, AuthState } from '../../types';

const initialState: AuthState = {
  user: null,
  tokens: null,
  isAuthenticated: false,
  isBootstrapping: false,
  error: null,
};

const authResponse: AuthResponse = {
  user: {
    id: 'u1',
    email: 'learner@example.com',
    fullName: 'Learner One',
    role: 'learner',
  },
  tokens: {
    accessToken: 'access-1',
    refreshToken: 'refresh-1',
    tokenType: 'bearer',
    expiresIn: 900,
  },
};

describe('authSlice', () => {
  it('starts unauthenticated', () => {
    expect(authReducer(undefined, { type: '@@init' })).toEqual(initialState);
  });

  it('authenticates on successful login', () => {
    const state = authReducer(initialState, {
      type: loginThunk.fulfilled.type,
      payload: authResponse,
    });
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe('learner@example.com');
    expect(state.tokens?.accessToken).toBe('access-1');
    expect(state.error).toBeNull();
  });

  it('surfaces a login failure without authenticating', () => {
    const pending = authReducer(initialState, { type: loginThunk.pending.type });
    expect(pending.isBootstrapping).toBe(true);

    const state = authReducer(pending, {
      type: loginThunk.rejected.type,
      payload: 'Invalid email or password',
    });
    expect(state.isAuthenticated).toBe(false);
    expect(state.error).toBe('Invalid email or password');
    expect(state.isBootstrapping).toBe(false);
  });

  it('replaces the token pair on refresh', () => {
    const authed = authReducer(initialState, {
      type: loginThunk.fulfilled.type,
      payload: authResponse,
    });
    const rotated: AuthResponse = {
      ...authResponse,
      tokens: { ...authResponse.tokens, accessToken: 'access-2', refreshToken: 'refresh-2' },
    };
    const state = authReducer(authed, {
      type: refreshThunk.fulfilled.type,
      payload: rotated,
    });
    expect(state.tokens?.accessToken).toBe('access-2');
    expect(state.tokens?.refreshToken).toBe('refresh-2');
    expect(state.isAuthenticated).toBe(true);
  });

  it('signs the user out when refresh fails', () => {
    const authed = authReducer(initialState, {
      type: loginThunk.fulfilled.type,
      payload: authResponse,
    });
    const state = authReducer(authed, { type: refreshThunk.rejected.type });
    expect(state.isAuthenticated).toBe(false);
    expect(state.tokens).toBeNull();
    expect(state.user).toBeNull();
  });

  it('clears the session on server logout', () => {
    const authed = authReducer(initialState, {
      type: loginThunk.fulfilled.type,
      payload: authResponse,
    });
    const state = authReducer(authed, { type: logoutThunk.fulfilled.type });
    expect(state.isAuthenticated).toBe(false);
    expect(state.tokens).toBeNull();
  });

  it('clears the session on local logout', () => {
    const authed = authReducer(initialState, {
      type: loginThunk.fulfilled.type,
      payload: authResponse,
    });
    expect(authReducer(authed, logout()).isAuthenticated).toBe(false);
  });

  it('clears an error without touching the session', () => {
    const errored: AuthState = { ...initialState, error: 'boom' };
    expect(authReducer(errored, clearAuthError()).error).toBeNull();
  });
});
