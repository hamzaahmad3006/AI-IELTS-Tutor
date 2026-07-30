/** Render tests for the five dashboard tabs. */

import React from 'react';
import { screen, waitFor } from '@testing-library/react-native';
import { Home } from '../Dashboard/Home/Home';
import { Practice } from '../Dashboard/Practice/Practice';
import { Progress } from '../Dashboard/Progress/Progress';
import { Coach } from '../Dashboard/Coach/Coach';
import { Profile } from '../Dashboard/Profile/Profile';
import { History } from '../History/History';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

describe('Home tab', () => {
  it('renders the greeting, predicted band and module tiles', async () => {
    renderWithProviders(<Home />);
    await waitFor(() => {
      expect(screen.getByText('PREDICTED IELTS BAND')).toBeTruthy();
    });
    expect(screen.getByText(/Hi, /)).toBeTruthy();
    ['Speaking', 'Writing', 'Reading', 'Listening'].forEach((module) => {
      expect(screen.getByText(module)).toBeTruthy();
    });
  });
});

describe('Practice tab', () => {
  it('lists all four modules', async () => {
    renderWithProviders(<Practice />);
    await waitFor(() => {
      expect(screen.getByText('Practice')).toBeTruthy();
    });
    ['Speaking', 'Writing', 'Reading', 'Listening'].forEach((module) => {
      expect(screen.getByText(module)).toBeTruthy();
    });
  });
});

describe('Progress tab', () => {
  it('renders overall band, prediction and per-module rows', async () => {
    renderWithProviders(<Progress />);
    await waitFor(() => {
      expect(screen.getByText('CURRENT OVERALL')).toBeTruthy();
    });
    expect(screen.getByText('PREDICTED BAND')).toBeTruthy();
    expect(screen.getByText('By module')).toBeTruthy();
    expect(screen.getByText('View attempt history')).toBeTruthy();
  });

  it('renders the band trend and module balance charts', async () => {
    renderWithProviders(<Progress />);
    await waitFor(() => {
      expect(screen.getByText('BAND TREND')).toBeTruthy();
    });
    expect(screen.getByTestId('band-trend-chart')).toBeTruthy();
    expect(screen.getByText('MODULE BALANCE')).toBeTruthy();
    expect(screen.getByTestId('module-balance-chart')).toBeTruthy();
  });
});

describe('Coach tab', () => {
  it('renders the coach message and recommendations', async () => {
    renderWithProviders(<Coach />);
    await waitFor(() => {
      expect(screen.getByText('Your AI Coach')).toBeTruthy();
    });
    expect(screen.getByText('Recommended focus')).toBeTruthy();
    expect(screen.getByText('Your current level')).toBeTruthy();
  });
});

describe('Profile tab', () => {
  it('renders the profile and settings', async () => {
    renderWithProviders(<Profile />);
    await waitFor(() => {
      expect(screen.getByText('Target band')).toBeTruthy();
    });
    expect(screen.getByText('Daily study time')).toBeTruthy();
    expect(screen.getByText('Starting levels')).toBeTruthy();
    expect(screen.getByText('Log Out')).toBeTruthy();
  });
});

describe('History screen', () => {
  it('renders the module switcher', async () => {
    renderWithProviders(<History />);
    await waitFor(() => {
      expect(screen.getByText('History')).toBeTruthy();
    });
    ['Writing', 'Speaking', 'Reading', 'Listening'].forEach((module) => {
      expect(screen.getByText(module)).toBeTruthy();
    });
  });
});
