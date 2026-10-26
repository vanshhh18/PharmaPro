import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import store from "./app/store";
import App from "./App";
import DashboardPage from "./pages/DashboardPage";
import InvestigationsListPage from "./pages/InvestigationsListPage";
import NewInvestigationPage from "./pages/NewInvestigationPage";
import InvestigationDetailPage from "./pages/InvestigationDetailPage";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />}>
            <Route index element={<DashboardPage />} />
            <Route path="investigations" element={<InvestigationsListPage />} />
            <Route path="investigations/new" element={<NewInvestigationPage />} />
            <Route path="investigations/:id" element={<InvestigationDetailPage />} />
            <Route path="*" element={<DashboardPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </Provider>
  </StrictMode>
);
