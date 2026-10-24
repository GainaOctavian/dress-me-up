import React from "react";
import { WebView } from "react-native-webview";

import { modelViewerHtml } from "./modelViewerHtml";

// Native: the viewer page in a WebView (ModelViewer.web.tsx: an iframe).
export const ModelViewer: React.FC<{ url: string; background: string }> = ({ url, background }) => (
  <WebView
    source={{ html: modelViewerHtml(url, background) }}
    originWhitelist={["*"]}
    style={{ flex: 1, backgroundColor: background }}
    scrollEnabled={false}
    // the page is ours; the GLB comes from the API's storage
    javaScriptEnabled
  />
);
