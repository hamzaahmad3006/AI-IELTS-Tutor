/**
 * Icon registry.
 *
 * Central list of icon identifiers used across the app. The <Icon /> component
 * (src/components/Icon) maps each name to an SVG path. Screens reference icons
 * by name (typed) rather than importing paths directly.
 */

export const ICONS = {
  // Navigation / tabs
  home: 'home',
  practice: 'practice',
  progress: 'progress',
  coach: 'coach',
  profile: 'profile',

  // Modules
  speaking: 'speaking',
  writing: 'writing',
  reading: 'reading',
  listening: 'listening',

  // Actions
  back: 'back',
  arrowRight: 'arrow-right',
  bell: 'bell',
  mic: 'mic',
  pause: 'pause',
  play: 'play',
  endCall: 'end-call',
  check: 'check',
  timer: 'timer',
  rocket: 'rocket',
  export: 'export',
  info: 'info',
  translate: 'translate',
  edit: 'edit',
  sparkle: 'sparkle',
  flame: 'flame',
} as const;

export type IconName = (typeof ICONS)[keyof typeof ICONS];
