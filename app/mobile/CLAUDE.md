# Mobile (Expo / React Native, TypeScript strict)

## Running

```bash
npm start
```

API base URL comes from `EXPO_PUBLIC_API_URL` (fallback in `src/config/constants.tsx` is a LAN IP for a physical device). Prefer setting the env var over editing the fallback. Typecheck with `npx tsc --noEmit`; no tests or linter are configured.

## Structure (`src/`)

- `api/` — one file per backend resource, built on `apiClient` (`client.ts`). Errors are thrown as `Error(responseText)`; use `errorMessage(e, fallback)` from `client.ts` to show FastAPI's `detail`.
- `api/cache.ts` — read-through AsyncStorage cache (`cached(key, fetcher, forceRefresh)`), no TTL. All keys go through `cacheKey()` (prefix `cache:`) so `logout` can wipe them with `clearCache()`. Mutations must write the updated object back to every cached copy (see `storeWardrobe` in `wardrobes.ts`), or lists go stale.
- `context/AuthContext.tsx` — token + current user, persisted in AsyncStorage (`auth:token`, `auth:user`). `isLoading` only covers the startup hydrate: `RootNavigation` swaps the whole tree for a spinner while it's true, so don't toggle it in `login`. Use `setUser` to update the current user (it persists too). Any 401 from `apiClient` calls `logout` (handler registered via `setUnauthorizedHandler`), so an expired token sends the user back to login.
- `context/ThemeContext.tsx` + `theme/colors.ts` — light/dark `ThemeColors`. Never hardcode colors; read them from `useTheme().colors`.
- `styles/<feature>.ts` — `createXStyles(colors)` factories, used as `useMemo(() => createXStyles(colors), [colors])`. Put styles here, not inline.
- `navigation/` — `RootNavigation` (auth vs app), bottom tabs in `AppNavigator`, one stack per tab when it needs one (`WardrobeNavigator`). Stacks export their `ParamList`; screens type props with `NativeStackScreenProps<ParamList, "Route">`.
- `components/ui/Chip.tsx` — the one pill used for filters/pickers (selected = filled). Don't hand-roll chip styles.
- `utils/confirm.ts` — `confirmDestructive(title, msg, confirmText)` for deletes/leave. Use it instead of `Alert.alert` with buttons: react-native-web ignores those buttons, so confirms silently never fire on web.
- Wardrobe stack: list → `WardrobeDetail` → `ItemForm` (edit for the item owner, read-only for other members; `canRemove` shows "Remove from this wardrobe") / `AddExistingItems`. Pushed screens show a themed header with only a back button, so their `SafeAreaView` uses `edges={["bottom","left","right"]}` (no double top inset).
- `Wardrobe.item_count` is client-only: filled from the list's `item_counts`, and refreshed by the detail screen (`storeWardrobe`) when it loads items. `storeWardrobe` merges, so it keeps client-only fields.
- Item photos: `api/images.ts` `uploadImage(token, uri, width)` shrinks to 1600px JPEG (`expo-image-manipulator`), asks the API for a presigned POST and uploads straight to storage, returning the `image_asset_id` to send with the item. `ItemFormScreen` uploads right after picking (library, plus camera on native), and Save waits for it. Show images with `expo-image` and `cacheKey: image_asset_id`: the signed URL changes on every fetch. URLs expire after 24h; `WardrobeDetailScreen` refetches once when an image fails to load.
- Outfits tab: `OutfitsNavigator` → `OutfitsList` (filter All / Personal / per wardrobe) → `OutfitDetail` → `OutfitForm` (pick wardrobe for new outfits, toggle items, live preview). `components/outfit/OutfitCanvas.tsx` is the single transform → style renderer (square canvas, `translate` = item center in 0..1, size = 40% × `scale`, z_index order); the plan 06 editor must reuse it. New items get positions from `utils/outfitLayout.ts` (`defaultLayout`, by category).
- The outfit form fetches wardrobes with `forceRefresh` (roles may have changed elsewhere). Deleting or removing an item drops the outfits cache (`dropCache`), because the backend pulls it out of outfits.
- `types/` — API shapes. The backend sends `_id`; users go through `normalizeUser` (in `api/users.ts`) so app code uses `user.id`. Wardrobes keep `_id`.

## E2E testing (Expo web, no phone needed)

1. Web deps without touching `package.json`: `npm install --no-save react-dom@<react version> react-native-web@0.21`.
2. An isolated API: a small launcher that imports `app.backend.api.src.main:app`, overrides `get_db` with a `mongomock` DB (patch `Cursor.to_list`), adds `CORSMiddleware(allow_origins=["*"])`, seeds users via `services.user.create_user`, and runs uvicorn on 8001. Never point E2E at the real DB.
3. `EXPO_PUBLIC_API_URL=http://localhost:8001 npx expo start --web --port 8090`, and drive it in the browser pane. On web, stub `window.confirm` to accept destructive confirms.
4. Photos: point the launcher's S3 env at the compose SeaweedFS (`S3_ENDPOINT_URL=http://localhost:8333`, dev keys). expo-image-picker's web picker opens its `<input type=file>` with `dispatchEvent(new MouseEvent("click"))`, so stub the OS dialog with a capturing `click` listener on `document` that sets `input.files` (a canvas-generated `File`) and dispatches `change`. Patching `HTMLInputElement.prototype.click` doesn't work.

## Gotchas

- Don't put `flex: 1` in a `FlatList`/`ScrollView` `contentContainerStyle`: it stops the list from scrolling. Use `listContent` / `scrollContent`, and `flexGrow: 1` for empty states.
- File uploads on native: Expo's `fetch` (SDK 52+) throws `Unsupported FormDataPart implementation` for React Native-style `{uri, name, type}` FormData parts. Append `new File(uri)` from `expo-file-system` (it implements `Blob`); on web, append a real `Blob`. See `api/images.ts`.
- Lists read from cache on focus (`useFocusEffect`), and pull-to-refresh passes `forceRefresh`.
