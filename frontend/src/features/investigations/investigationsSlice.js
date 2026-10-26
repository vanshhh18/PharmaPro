import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { getJson, patchJson, postJson } from "../../api/client";

const pathWithQuery = (status, limit, offset) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (limit) params.set("limit", String(limit));
  if (offset) params.set("offset", String(offset));
  const qs = params.toString();
  return `/api/investigations${qs ? `?${qs}` : ""}`;
};

export const fetchInvestigations = createAsyncThunk(
  "investigations/fetchList",
  ({ status } = {}) => getJson(pathWithQuery(status))
);

export const fetchInvestigation = createAsyncThunk(
  "investigations/fetchOne",
  (id) => getJson(`/api/investigations/${id}`)
);

export const createInvestigation = createAsyncThunk(
  "investigations/create",
  (payload) => postJson("/api/investigations", payload)
);

export const updateInvestigation = createAsyncThunk(
  "investigations/update",
  ({ id, ...patch }) => patchJson(`/api/investigations/${id}`, patch)
);

export const archiveInvestigation = createAsyncThunk(
  "investigations/archive",
  (id) => postJson(`/api/investigations/${id}/archive`)
);

export const reopenInvestigation = createAsyncThunk(
  "investigations/reopen",
  (id) => postJson(`/api/investigations/${id}/reopen`)
);

const investigationsSlice = createSlice({
  name: "investigations",
  initialState: {
    list: [],
    listLoading: false,
    listError: null,
    current: null,
    currentLoading: false,
    currentError: null,
    saving: false,
    saveError: null,
    lastSaved: null,
    notice: null,
  },
  reducers: {
    clearNotice(state) {
      state.notice = null;
      state.saveError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInvestigations.pending, (state) => {
        state.listLoading = true;
        state.listError = null;
      })
      .addCase(fetchInvestigations.fulfilled, (state, action) => {
        state.listLoading = false;
        state.list = action.payload;
      })
      .addCase(fetchInvestigations.rejected, (state, action) => {
        state.listLoading = false;
        state.listError = action.error.message || "Could not load investigations";
      })
      .addCase(fetchInvestigation.pending, (state) => {
        state.currentLoading = true;
        state.currentError = null;
        state.current = null;
      })
      .addCase(fetchInvestigation.fulfilled, (state, action) => {
        state.currentLoading = false;
        state.current = action.payload;
      })
      .addCase(fetchInvestigation.rejected, (state, action) => {
        state.currentLoading = false;
        state.currentError = action.error.message || "Could not load investigation";
      })
      .addCase(createInvestigation.pending, (state) => {
        state.saving = true;
        state.saveError = null;
      })
      .addCase(createInvestigation.fulfilled, (state, action) => {
        state.saving = false;
        state.lastSaved = action.payload;
        state.notice = "Investigation saved.";
      })
      .addCase(createInvestigation.rejected, (state, action) => {
        state.saving = false;
        state.saveError = action.error.message || "Could not save investigation";
      })
      .addCase(updateInvestigation.pending, (state) => {
        state.saving = true;
        state.saveError = null;
      })
      .addCase(updateInvestigation.fulfilled, (state, action) => {
        state.saving = false;
        state.current = action.payload;
        state.notice = "Changes saved.";
      })
      .addCase(updateInvestigation.rejected, (state, action) => {
        state.saving = false;
        state.saveError = action.error.message || "Could not save changes";
      })
      .addCase(archiveInvestigation.pending, (state) => {
        state.saving = true;
        state.saveError = null;
      })
      .addCase(archiveInvestigation.fulfilled, (state, action) => {
        state.saving = false;
        state.current = action.payload;
        state.notice = "Investigation archived.";
      })
      .addCase(archiveInvestigation.rejected, (state, action) => {
        state.saving = false;
        state.saveError = action.error.message || "Could not archive";
      })
      .addCase(reopenInvestigation.pending, (state) => {
        state.saving = true;
        state.saveError = null;
      })
      .addCase(reopenInvestigation.fulfilled, (state, action) => {
        state.saving = false;
        state.current = action.payload;
        state.notice = "Investigation reopened.";
      })
      .addCase(reopenInvestigation.rejected, (state, action) => {
        state.saving = false;
        state.saveError = action.error.message || "Could not reopen";
      });
  },
});

export const { clearNotice } = investigationsSlice.actions;

export const selectInvestigations = (state) => state.investigations;
export default investigationsSlice.reducer;
