import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import App from "./App";
import FeedPage from "./pages/FeedPage";
import SearchPage from "./pages/SearchPage";
import TimelinePage from "./pages/TimelinePage";
import StatsPage from "./pages/StatsPage";
import MemoryOpsPage from "./pages/MemoryOpsPage";
import { SettingsProvider } from "./settings";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Cannot find root element");
}

createRoot(rootElement).render(
  <StrictMode>
    <SettingsProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<App />}>
              <Route index element={<SearchPage />} />
              <Route path="feed" element={<FeedPage />} />
              <Route path="timeline" element={<TimelinePage />} />
              <Route path="stats" element={<StatsPage />} />
              <Route path="ops" element={<MemoryOpsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </SettingsProvider>
  </StrictMode>
);
