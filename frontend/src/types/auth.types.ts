/** Authentication domain types. */

import type { UserRole } from './user.types';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  fullName: string;
  email: string;
  password: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: 'bearer';
  expiresIn: number;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
}

export interface AuthResponse {
  user: AuthenticatedUser;
  tokens: AuthTokens;
}

export interface AuthState {
  user: AuthenticatedUser | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  error: string | null;
}

export interface FormFieldError {
  field: string;
  message: string;
}
