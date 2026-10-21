// Skia on web runs on CanvasKit (wasm), which must be loaded before any Skia
// component renders. The wasm (8 MB) comes from the CDN, matching the
// canvaskit-wasm version react-native-skia depends on (web is for dev/E2E).
// Web-only file: CanvasKit's JS requires `fs`, which breaks native bundles.
import { LoadSkiaWeb } from "@shopify/react-native-skia/lib/module/web";

const version: string = require("canvaskit-wasm/package.json").version;

export const loadSkia = () =>
  LoadSkiaWeb({
    locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/canvaskit-wasm@${version}/bin/full/${file}`,
  });
