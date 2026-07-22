/**
 * Elevation / shadow tokens (Tonal Layers + Ambient Shadows).
 * Cross-platform: iOS shadow* props + Android elevation.
 */

import type { ViewStyle } from 'react-native';
import { PALETTE } from './colors';

type Shadow = Pick<
  ViewStyle,
  | 'shadowColor'
  | 'shadowOffset'
  | 'shadowOpacity'
  | 'shadowRadius'
  | 'elevation'
>;

export const SHADOWS = {
  none: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  // Level 1 — cards (soft, diffused, indigo-tinted)
  card: {
    shadowColor: PALETTE.indigo,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 20,
    elevation: 4,
  },
  // Level 2 — modals / floating action buttons
  elevated: {
    shadowColor: PALETTE.ink,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.2,
    shadowRadius: 24,
    elevation: 10,
  },
  // CTA buttons
  button: {
    shadowColor: PALETTE.teal,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
  },
} as const satisfies Record<string, Shadow>;

export type ShadowToken = keyof typeof SHADOWS;
