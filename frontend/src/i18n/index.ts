/**
 * Localisation.
 *
 * Deliberately small: a dictionary, a lookup, and a device-locale check. No
 * i18n library, because the app has one language today and pulling in a
 * framework to hold one dictionary buys nothing but a dependency to keep
 * current. The shape here is the one a library expects, so swapping to
 * i18next later is a change of implementation rather than of every call site.
 *
 * What this *is* for right now is getting the strings out of the components.
 * A string in JSX cannot be reviewed for tone, reused, or translated, and the
 * work of extracting them is the same whether a library is involved or not.
 *
 * IELTS terminology is not translated. "Band", "Task 1", "cue card" are the
 * words on the real exam paper in every country it is sat in, and localising
 * them would teach a learner vocabulary the examiner will not use.
 */

import { NativeModules, Platform } from 'react-native';

import { en } from './en';

export type TranslationKey = keyof typeof en;
type Params = Record<string, string | number>;

/** Every supported locale. English is the source of truth for the key set. */
const DICTIONARIES = { en } as const;

export type Locale = keyof typeof DICTIONARIES;

export const DEFAULT_LOCALE: Locale = 'en';

/**
 * The device's language, if the app has it.
 *
 * Read defensively: the native modules that expose it differ by platform and
 * have moved between React Native versions, and a missing locale should mean
 * English rather than a crash on the first render.
 */
export const deviceLocale = (): Locale => {
  try {
    const raw =
      Platform.OS === 'ios'
        ? (NativeModules.SettingsManager?.settings?.AppleLocale as
            | string
            | undefined) ??
          (
            NativeModules.SettingsManager?.settings?.AppleLanguages as
              | string[]
              | undefined
          )?.[0]
        : (NativeModules.I18nManager?.localeIdentifier as string | undefined);

    const language = raw?.split(/[-_]/)[0]?.toLowerCase();
    if (language && language in DICTIONARIES) {
      return language as Locale;
    }
  } catch {
    // Native module missing (test runner, or a version that moved it).
  }
  return DEFAULT_LOCALE;
};

let activeLocale: Locale = DEFAULT_LOCALE;

export const setLocale = (locale: Locale): void => {
  activeLocale = locale;
};

export const getLocale = (): Locale => activeLocale;

/**
 * Substitute {name} placeholders.
 *
 * An unknown placeholder is left in the string rather than replaced with
 * "undefined": a visible {count} is obviously a bug to whoever sees it, where
 * "You have undefined items left" reads like a broken app to the user and like
 * working software to everyone else.
 */
const interpolate = (template: string, params?: Params): string => {
  if (!params) {
    return template;
  }
  return template.replace(/\{(\w+)\}/g, (whole, key: string) =>
    key in params ? String(params[key]) : whole,
  );
};

/**
 * Look up a translation.
 *
 * A missing key returns the key itself. That is deliberate: showing
 * "speaking.part2.prepare" on screen is ugly and unmistakable, where falling
 * back to an empty string produces a blank space nobody reports.
 */
export const t = (key: TranslationKey, params?: Params): string => {
  const dictionary = DICTIONARIES[activeLocale] ?? en;
  const template = (dictionary as Record<string, string>)[key] ?? en[key];
  if (template === undefined) {
    return key;
  }
  return interpolate(template, params);
};
