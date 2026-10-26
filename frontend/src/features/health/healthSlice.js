import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { fetchJson } from "../../api/client";

export const loadHealth = createAsyncThunk("health/load", async () => {
  return fetchJson("/api/health");
});

const healthSlice = createSlice({
  name: "health",
  initialState: {
    data: null,
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(loadHealth.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loadHealth.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;
      })
      .addCase(loadHealth.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Health check failed";
      });
  },
});

export const selectHealth = (state) => state.health;

export default healthSlice.reducer;
