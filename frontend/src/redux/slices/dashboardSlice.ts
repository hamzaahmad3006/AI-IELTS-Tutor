/** Dashboard slice with async fetch thunk. */

import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { dashboardApi } from '../../api';
import type { ApiProblem, AsyncState, DashboardData } from '../../types';

type DashboardSliceState = AsyncState<DashboardData>;

const initialState: DashboardSliceState = {
  data: null,
  status: 'idle',
  error: null,
};

export const fetchDashboardThunk = createAsyncThunk<
  DashboardData,
  void,
  { rejectValue: string }
>('dashboard/fetch', async (_, { rejectWithValue }) => {
  try {
    return await dashboardApi.getOverview();
  } catch (error) {
    return rejectWithValue((error as ApiProblem).title);
  }
});

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboardThunk.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(fetchDashboardThunk.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.data = action.payload;
      })
      .addCase(fetchDashboardThunk.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload ?? 'Failed to load dashboard';
      });
  },
});

export const dashboardReducer = dashboardSlice.reducer;
