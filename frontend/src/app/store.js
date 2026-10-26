import { configureStore } from "@reduxjs/toolkit";
import healthReducer from "../features/health/healthSlice";
import dashboardReducer from "../features/dashboard/dashboardSlice";
import investigationsReducer from "../features/investigations/investigationsSlice";
import analysisReducer from "../features/analysis/analysisSlice";

export function makeStore() {
  return configureStore({
    reducer: {
      health: healthReducer,
      dashboard: dashboardReducer,
      investigations: investigationsReducer,
      analysis: analysisReducer,
    },
  });
}

const store = makeStore();
export default store;
