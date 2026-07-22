/** Static asset registry. Import assets from here, not by raw path. */

import type { ImageSourcePropType } from 'react-native';

export const IMAGES: Record<'logo', ImageSourcePropType> = {
  logo: require('./images/logo.png'),
};
