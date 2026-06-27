import React from "react";
import ReactDOM from "react-dom/client";
import "@voca/ui/tokens.css";
import "@voca/ui/components.css";
import "@voca/ui/fonts";
import "./app.css";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
