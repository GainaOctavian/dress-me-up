// The page shown by ModelViewer: Google's <model-viewer> (drag to turn,
// pinch / wheel to zoom) on the outfit's GLB. Loaded from jsDelivr, like
// CanvasKit (loadSkia.web.ts).
export const modelViewerHtml = (url: string, background: string) => `<!doctype html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<script type="module" src="https://cdn.jsdelivr.net/npm/@google/model-viewer@4.0.0/dist/model-viewer.min.js"></script>
<style>html,body{margin:0;height:100%;background:${background}}model-viewer{width:100%;height:100%;--poster-color:transparent}</style>
</head><body>
<model-viewer src="${url.replace(/"/g, "&quot;")}" camera-controls touch-action="none"
  shadow-intensity="0.6" exposure="1.1" environment-image="neutral"
  camera-orbit="0deg 85deg auto" interaction-prompt="auto"></model-viewer>
</body></html>`;
