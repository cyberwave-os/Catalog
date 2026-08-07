import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Viewer3D } from "./Viewer3D";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Viewer3D />
  </StrictMode>,
);
