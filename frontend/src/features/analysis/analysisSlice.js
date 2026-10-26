import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { postForm, postJson } from "../../api/client";

export const runAnalysis = createAsyncThunk(
  "analysis/run",
  (text) => postJson("/api/analysis", { text })
);

export const intakeText = createAsyncThunk(
  "analysis/intakeText",
  (text) => postJson("/api/reports/intake/text", { text })
);

export const intakeFile = createAsyncThunk(
  "analysis/intakeFile",
  (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return postForm("/api/reports/intake/file", formData);
  }
);

const analysisSlice = createSlice({
  name: "analysis",
  initialState: {
    intake: null,
    analysis: null,
    loading: false,
    error: null,
  },
  reducers: {
    clearResults(state) {
      state.intake = null;
      state.analysis = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(runAnalysis.pending, (state) => {
        state.loading = true;
        state.error = null;
        state.analysis = null;
      })
      .addCase(runAnalysis.fulfilled, (state, action) => {
        state.loading = false;
        state.analysis = action.payload;
      })
      .addCase(runAnalysis.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "AI analysis failed";
      })
      .addCase(intakeText.pending, (state) => {
        state.loading = true;
        state.error = null;
        state.intake = null;
      })
      .addCase(intakeText.fulfilled, (state, action) => {
        state.loading = false;
        state.intake = action.payload;
      })
      .addCase(intakeText.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Report intake failed";
      })
      .addCase(intakeFile.pending, (state) => {
        state.loading = true;
        state.error = null;
        state.intake = null;
      })
      .addCase(intakeFile.fulfilled, (state, action) => {
        state.loading = false;
        state.intake = action.payload;
      })
      .addCase(intakeFile.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "File intake failed";
      });
  },
});

export const { clearResults } = analysisSlice.actions;

export const selectAnalysis = (state) => state.analysis;
export default analysisSlice.reducer;
