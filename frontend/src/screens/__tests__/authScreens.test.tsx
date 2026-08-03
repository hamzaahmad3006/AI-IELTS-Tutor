/** Render + interaction tests for the auth screens. */

import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Login } from '../Auth/Login/Login';
import { Register } from '../Auth/Register/Register';
import { ForgotPassword } from '../Auth/ForgotPassword/ForgotPassword';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

describe('Login screen', () => {
  it('renders the form', () => {
    renderWithProviders(<Login />);
    expect(screen.getByText('Log In')).toBeTruthy();
    expect(screen.getByPlaceholderText('you@example.com')).toBeTruthy();
  });

  it('rejects an invalid email and does not submit', async () => {
    renderWithProviders(<Login />);
    fireEvent.changeText(
      screen.getByPlaceholderText('you@example.com'),
      'not-an-email',
    );
    fireEvent.changeText(
      screen.getByPlaceholderText('••••••••'),
      'StrongPass123',
    );
    fireEvent.press(screen.getByText('Log In'));

    await waitFor(() => {
      expect(screen.getByText('Enter a valid email address')).toBeTruthy();
    });
  });

  it('rejects a short password', async () => {
    renderWithProviders(<Login />);
    fireEvent.changeText(
      screen.getByPlaceholderText('you@example.com'),
      'learner@example.com',
    );
    fireEvent.changeText(screen.getByPlaceholderText('••••••••'), 'short');
    fireEvent.press(screen.getByText('Log In'));

    await waitFor(() => {
      expect(
        screen.getByText('Password must be at least 8 characters'),
      ).toBeTruthy();
    });
  });
});

describe('Register screen', () => {
  it('renders the form', () => {
    renderWithProviders(<Register />);
    expect(screen.getByText('Create your account')).toBeTruthy();
    expect(screen.getByPlaceholderText('Sarah Ahmed')).toBeTruthy();
  });

  it('requires a full name', async () => {
    renderWithProviders(<Register />);
    fireEvent.changeText(screen.getByPlaceholderText('Sarah Ahmed'), 'A');
    fireEvent.changeText(
      screen.getByPlaceholderText('you@example.com'),
      'learner@example.com',
    );
    fireEvent.changeText(
      screen.getByPlaceholderText('At least 8 characters'),
      'StrongPass123',
    );
    fireEvent.press(screen.getByText('Create Account'));

    await waitFor(() => {
      expect(screen.getByText('Enter your full name')).toBeTruthy();
    });
  });
});

describe('ForgotPassword screen', () => {
  it('renders and validates the email', async () => {
    renderWithProviders(<ForgotPassword />);
    expect(screen.getByText('Reset password')).toBeTruthy();

    fireEvent.changeText(screen.getByPlaceholderText('you@example.com'), 'bad');
    fireEvent.press(screen.getByText('Send reset link'));

    await waitFor(() => {
      expect(screen.getByText('Enter a valid email address')).toBeTruthy();
    });
  });
});
