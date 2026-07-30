/** Static asset registry. Import assets from here, not by raw path. */

import type { ImageSourcePropType } from 'react-native';

/**
 * `logo` is the bare mark (speech bubble + ascending bands) for tight spaces;
 * `logoWordmark` pairs it with the "IELTS Master" name for splash/auth screens.
 */
export const IMAGES: Record<'logo' | 'logoWordmark', ImageSourcePropType> = {
  logo: require('./images/logo.png'),
  logoWordmark: require('./images/logo_wordmark.png'),
};
