# Mobile (Expo / React Native, TypeScript strict)

## Running

```bash
npm start
```

API base URL comes from `EXPO_PUBLIC_API_URL` (fallback in `src/config/constants.tsx` is a LAN IP for a physical device). Prefer setting the env var over editing the fallback. Typecheck with `npx tsc --noEmit`; no tests or linter are configured.

## Structure (`src/`)

- `api/` — one file per backend resource, built on `apiClient` (`client.ts`). Errors are thrown as `Error(responseText)`; FastAPI's `{"detail": ...}` is inside `message`.
- `api/cache.ts` — read-through AsyncStorage cache (`cached(key, fetcher, forceRefresh)`), no TTL. All keys go through `cacheKey()` (prefix `cache:`) so `logout` can wipe them with `clearCache()`. Mutations must write the updated object back to every cached copy (see `storeWardrobe` in `wardrobes.ts`), or lists go stale.
- `context/AuthContext.tsx` — token + current user, persisted in AsyncStorage (`auth:token`, `auth:user`). `isLoading` only covers the startup hydrate: `RootNavigation` swaps the whole tree for a spinner while it's true, so don't toggle it in `login`. Use `setUser` to update the current user (it persists too).
- `context/ThemeContext.tsx` + `theme/colors.ts` — light/dark `ThemeColors`. Never hardcode colors; read them from `useTheme().colors`.
- `styles/<feature>.ts` — `createXStyles(colors)` factories, used as `useMemo(() => createXStyles(colors), [colors])`. Put styles here, not inline.
- `navigation/` — `RootNavigation` (auth vs app), bottom tabs in `AppNavigator`, one stack per tab when it needs one (`WardrobeNavigator`). Stacks export their `ParamList`; screens type props with `NativeStackScreenProps<ParamList, "Route">`.
- `types/` — API shapes. The backend sends `_id`; users go through `normalizeUser` (in `api/users.ts`) so app code uses `user.id`. Wardrobes keep `_id`.

## Gotchas

- Don't put `flex: 1` in a `FlatList`/`ScrollView` `contentContainerStyle`: it stops the list from scrolling. Use `listContent` / `scrollContent`, and `flexGrow: 1` for empty states.
- Lists read from cache on focus (`useFocusEffect`), and pull-to-refresh passes `forceRefresh`.
