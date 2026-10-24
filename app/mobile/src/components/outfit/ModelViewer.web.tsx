import React from "react";

import { modelViewerHtml } from "./modelViewerHtml";

// Web: react-native-webview doesn't run in the browser, an iframe does.
export const ModelViewer: React.FC<{ url: string; background: string }> = ({ url, background }) =>
  React.createElement("iframe", {
    srcDoc: modelViewerHtml(url, background),
    title: "Outfit in 3D",
    style: { flex: 1, width: "100%", height: "100%", border: 0, backgroundColor: background },
  });
