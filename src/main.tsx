import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { BrowserRouter } from "react-router-dom";
import ConfirmDialogHost from './icui/components/ui/ConfirmDialogHost';
import PromptDialogHost from './icui/components/ui/PromptDialogHost';

// Fix potential double slash issue with basename
const baseUrl = import.meta.env.BASE_URL || "/";
const basename = baseUrl === "/" ? undefined : baseUrl;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
  <App />
  {/* Global dialog hosts */}
  <ConfirmDialogHost />
  <PromptDialogHost />
    </BrowserRouter>
  </React.StrictMode>,
);
