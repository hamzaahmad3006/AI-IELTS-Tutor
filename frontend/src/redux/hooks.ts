/** Typed Redux hooks — use these instead of the untyped base hooks. */

import { useDispatch, useSelector } from 'react-redux';
import type { AppDispatch, RootState } from './store';

export const useAppDispatch = (): AppDispatch => useDispatch<AppDispatch>();

export const useAppSelector = useSelector.withTypes<RootState>();
