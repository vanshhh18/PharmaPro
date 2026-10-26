import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { getJson } from "../../api/client";

export const fetchDashboard = createAsyncThunk(
  "dashboard/fetch",
  () => getJson("/api/investigations/dashboard")
);

const dashboardSlice = createSlice({
  name: "dashboard",
  initialState: { counts: null, loading: false, error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboard.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboard.fulfilled, (state, action) => {
        state.loading = false;
        state.counts = action.payload;
      })
      .addCase(fetchDashboard.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Could not load dashboard counts";
      });
  },
});

export const selectDashboard = (state) => state.dashboard;
export default dashboardSlice.reducer;
