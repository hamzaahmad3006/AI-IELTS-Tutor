/** Theme (light/dark) slice. */

import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { ThemeMode } from '../../constants';

export interface ThemeSliceState {
  mode: ThemeMode;
}

const initialState: ThemeSliceState = {
  mode: 'light',
};

const themeSlice = createSlice({
  name: 'theme',
  initialState,
  reducers: {
    setThemeMode(state, action: PayloadAction<ThemeMode>): void {
      state.mode = action.payload;
    },
    toggleTheme(state): void {
      state.mode = state.mode === 'light' ? 'dark' : 'light';
    },
  },
});

export const { setThemeMode, toggleTheme } = themeSlice.actions;
export const themeReducer = themeSlice.reducer;
