import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import { ErrorBoundary } from "./ErrorBoundary";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <ErrorBoundary>
    <StrictMode>
      <AuthProvider>
        <App />
      </AuthProvider>
    </StrictMode>
  </ErrorBoundary>,
);
