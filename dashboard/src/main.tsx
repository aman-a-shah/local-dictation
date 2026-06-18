import React from "react";
import ReactDOM from "react-dom/client";
import "@local-dictation/ui/tokens.css";
import "@local-dictation/ui/components.css";
import "@local-dictation/ui/fonts";
import "./app.css";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
