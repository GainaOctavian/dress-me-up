import { registerRootComponent } from "expo";

import { loadSkia } from "./src/loadSkia";

// registerRootComponent calls AppRegistry.registerComponent('main', () => App);
// It also ensures that whether you load the app in Expo Go or in a native build,
// the environment is set up appropriately.
// App is required after loadSkia: on web, Skia must be loaded before any Skia import runs.
loadSkia().then(() => registerRootComponent(require("./App").default));
