/** Hook returning the active Theme object based on the persisted theme mode. */

import { getTheme, type Theme } from '@constants';
import { useAppSelector } from '@redux';

export const useTheme = (): Theme => {
  const mode = useAppSelector(state => state.theme.mode);
  return getTheme(mode);
};
