import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { createItemStyles } from "../../styles/item";
import {
  createItem,
  deleteItem,
  removeItemFromWardrobe,
  updateItem,
} from "../../api/items";
import { errorMessage } from "../../api/client";
import { uploadImage, waitForProcessing } from "../../api/images";
import { subcategoryLabel, useLayering } from "../../api/meta";
import { ITEM_CATEGORIES, ItemCategory } from "../../types/item";
import { Chip } from "../../components/ui/Chip";
import { confirmDestructive } from "../../utils/confirm";
import { WardrobeStackParamList } from "../../navigation/WardrobeNavigator";

type Props = NativeStackScreenProps<WardrobeStackParamList, "ItemForm">;

// "a, b,, c " -> ["a", "b", "c"]
const parseList = (text: string) =>
  text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

export const ItemFormScreen: React.FC<Props> = ({ route, navigation }) => {
  const { wardrobeId, item, canRemove = false } = route.params;
  const { token, user } = useAuth();
  // Only the item's owner edits it; others (members) see it read-only.
  const editable = !item || item.owner_id === user?.id;
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  const itemStyles = useMemo(() => createItemStyles(colors), [colors]);

  const [name, setName] = useState(item?.name ?? "");
  const [categories, setCategories] = useState<ItemCategory[]>(
    item?.categories ?? []
  );
  // precise type (plan 11): options depend on the chosen categories
  const layering = useLayering();
  const [subcategory, setSubcategory] = useState<string | null>(item?.subcategory ?? null);
  const categoriesRef = useRef(categories);
  categoriesRef.current = categories;
  const [tags, setTags] = useState(item?.tags.join(", ") ?? "");
  const [itemColors, setItemColors] = useState(item?.colors.join(", ") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // photo: preview (local file or current image_url) + id of a new upload
  const [photoUri, setPhotoUri] = useState<string | null>(item?.image_url ?? null);
  const [newImageId, setNewImageId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  // worker: background removal + suggested category/tags/colors
  const [analyzing, setAnalyzing] = useState(false);
  const latestUpload = useRef<string | null>(null);
  const mounted = useRef(true);
  useEffect(() => () => { mounted.current = false; }, []);

  // Swap in the cutout and fill only what the user left empty.
  // Saving early is fine: the worker also fills the saved item.
  const applySuggestions = async (imageAssetId: string) => {
    if (!token) return;
    setAnalyzing(true);
    try {
      const s = await waitForProcessing(token, imageAssetId);
      if (!mounted.current || latestUpload.current !== imageAssetId) return;
      if (s.status !== "processed") return; // keep the original photo
      setPhotoUri(s.image_url);
      if (s.category) setCategories((prev) => (prev.length ? prev : [s.category!]));
      // suggested type only if it agrees with the categories in the form
      const cats = categoriesRef.current.length ? categoriesRef.current : [s.category];
      if (s.subcategory && s.category && cats.includes(s.category)) {
        setSubcategory((prev) => prev ?? s.subcategory);
      }
      setTags((prev) => (prev.trim() ? prev : s.tags.join(", ")));
      setItemColors((prev) => (prev.trim() ? prev : s.colors.join(", ")));
    } catch (e) {
      console.log("Image analysis status failed", e);
    } finally {
      if (mounted.current && latestUpload.current === imageAssetId) setAnalyzing(false);
    }
  };

  // Pick → upload right away, so Save only sends the image_asset_id.
  const pickPhoto = async (source: "library" | "camera") => {
    if (!token) return;
    const perm =
      source === "camera"
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      setError(
        source === "camera"
          ? "Camera access is needed to take a photo. Enable it in Settings."
          : "Photo access is needed to choose a photo. Enable it in Settings."
      );
      return;
    }
    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: ["images"],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 1,
    };
    const result =
      source === "camera"
        ? await ImagePicker.launchCameraAsync(options)
        : await ImagePicker.launchImageLibraryAsync(options);
    if (result.canceled) return;

    const asset = result.assets[0];
    const previous = photoUri;
    setPhotoUri(asset.uri);
    setUploading(true);
    setError(null);
    try {
      const id = await uploadImage(token, asset.uri, asset.width);
      latestUpload.current = id;
      setNewImageId(id);
      void applySuggestions(id);
    } catch (e) {
      console.log("Photo upload failed", e);
      setError(errorMessage(e, "Could not upload the photo. Please try again."));
      setPhotoUri(previous);
      setNewImageId(null);
    } finally {
      setUploading(false);
    }
  };

  const toggleCategory = (c: ItemCategory) => {
    const next = categories.includes(c)
      ? categories.filter((x) => x !== c)
      : [...categories, c];
    setCategories(next);
    // drop a type that no longer matches any chosen category
    const subCat = subcategory && layering?.subcategories[subcategory]?.category;
    if (subCat && !next.includes(subCat)) setSubcategory(null);
  };

  const typeOptions = Object.entries(layering?.subcategories ?? {}).filter(
    ([, info]) => categories.includes(info.category)
  );

  // Runs an API call, then goes back to the wardrobe on success.
  const run = async (
    action: (token: string) => Promise<unknown>,
    fallbackError: string
  ) => {
    if (!token) return;
    setBusy(true);
    try {
      await action(token);
      navigation.goBack();
    } catch (e) {
      console.log(fallbackError, e);
      setError(errorMessage(e, fallbackError));
      setBusy(false);
    }
  };

  const handleSave = () => {
    const payload = {
      name: name.trim(),
      categories,
      ...(subcategory ? { subcategory } : {}),
      tags: parseList(tags),
      colors: parseList(itemColors),
      ...(newImageId ? { image_asset_id: newImageId } : {}),
    };
    void run(
      (t) =>
        item
          ? updateItem(t, item._id, payload)
          : createItem(t, wardrobeId, payload),
      "Could not save item. Please try again."
    );
  };

  const handleRemoveFromWardrobe = () =>
    item &&
    run(
      (t) => removeItemFromWardrobe(t, wardrobeId, item._id),
      "Could not remove item. Please try again."
    );

  const handleDelete = async () => {
    if (!item) return;
    const ok = await confirmDestructive(
      "Delete item",
      `Delete "${item.name}" from all wardrobes? This cannot be undone.`
    );
    if (ok) {
      void run(
        (t) => deleteItem(t, item),
        "Could not delete item. Please try again."
      );
    }
  };

  const canSave = !busy && !uploading && name.trim().length > 0;

  return (
    <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Text style={styles.title}>
            {!item ? "New item" : editable ? "Edit item" : item.name}
          </Text>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={[styles.sectionCard, styles.form]}>
          <View style={itemStyles.photo}>
            {photoUri ? (
              <Image
                source={{ uri: photoUri }}
                style={{ width: "100%", height: "100%" }}
                contentFit="contain"
                accessibilityLabel="Item photo"
              />
            ) : (
              <Text style={itemStyles.empty}>
                {editable ? "No photo yet" : "No photo"}
              </Text>
            )}
            {uploading && (
              <View style={itemStyles.uploadOverlay}>
                <ActivityIndicator color={colors.buttonTextOnPrimary} />
              </View>
            )}
          </View>

          {analyzing && (
            <Text style={itemStyles.hint}>
              Removing the background and detecting colors and tags…
            </Text>
          )}

          {editable && (
            <View style={styles.buttonRow}>
              <TouchableOpacity
                onPress={() => pickPhoto("library")}
                disabled={uploading || busy}
                style={[styles.secondaryButton, { flex: 1 }]}
              >
                <Text style={styles.secondaryButtonText}>
                  {photoUri ? "Change photo" : "Choose photo"}
                </Text>
              </TouchableOpacity>
              {/* no camera in the browser */}
              {Platform.OS !== "web" && (
                <TouchableOpacity
                  onPress={() => pickPhoto("camera")}
                  disabled={uploading || busy}
                  style={[styles.secondaryButton, { flex: 1 }]}
                >
                  <Text style={styles.secondaryButtonText}>Take photo</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          <Text style={styles.metaLabel}>Name</Text>
          <TextInput
            value={name}
            onChangeText={setName}
            editable={editable}
            style={styles.input}
            placeholder="e.g. Blue denim jacket"
            placeholderTextColor={colors.textMuted}
          />

          <Text style={styles.metaLabel}>Categories</Text>
          <View style={itemStyles.chipWrap}>
            {/* read-only: show just the item's categories */}
            {(editable ? ITEM_CATEGORIES : categories).map((c) => (
              <Chip
                key={c}
                label={c.toUpperCase()}
                selected={categories.includes(c)}
                onPress={editable ? () => toggleCategory(c) : undefined}
              />
            ))}
          </View>

          <Text style={styles.metaLabel}>Type</Text>
          {!editable ? (
            <Text style={styles.metaValue}>
              {subcategory ? subcategoryLabel(layering, subcategory) : "—"}
            </Text>
          ) : categories.length === 0 ? (
            <Text style={itemStyles.hint}>Pick a category to choose the exact type.</Text>
          ) : (
            <View style={itemStyles.chipWrap}>
              {typeOptions.map(([key, info]) => (
                <Chip
                  key={key}
                  label={info.label}
                  selected={subcategory === key}
                  onPress={() => setSubcategory(subcategory === key ? null : key)}
                />
              ))}
            </View>
          )}

          <Text style={styles.metaLabel}>Tags</Text>
          <TextInput
            value={tags}
            onChangeText={setTags}
            editable={editable}
            style={styles.input}
            placeholder="summer, casual"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
          />

          <Text style={styles.metaLabel}>Colors</Text>
          <TextInput
            value={itemColors}
            onChangeText={setItemColors}
            editable={editable}
            style={styles.input}
            placeholder="blue, white"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="none"
          />
          {editable && (
            <Text style={itemStyles.hint}>Separate tags and colors with commas.</Text>
          )}

          {editable && (
          <View style={styles.buttonRow}>
            <TouchableOpacity
              onPress={handleSave}
              disabled={!canSave}
              style={[
                styles.primaryButton,
                { flex: 1 },
                !canSave && styles.buttonDisabled,
              ]}
            >
              <Text style={styles.primaryButtonText}>
                {uploading ? "Uploading photo…" : busy ? "Saving…" : "Save"}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => navigation.goBack()}
              disabled={busy}
              style={[styles.secondaryButton, { flex: 1 }]}
            >
              <Text style={styles.secondaryButtonText}>Cancel</Text>
            </TouchableOpacity>
          </View>
          )}
        </View>

        {item && (editable || canRemove) && (
          <View style={[styles.sectionCard, styles.form]}>
            <TouchableOpacity
              onPress={handleRemoveFromWardrobe}
              disabled={busy}
              style={styles.secondaryButton}
            >
              <Text style={styles.secondaryButtonText}>
                Remove from this wardrobe
              </Text>
            </TouchableOpacity>
            {editable && (
              <TouchableOpacity
                onPress={handleDelete}
                disabled={busy}
                style={styles.secondaryButton}
              >
                <Text style={[styles.secondaryButtonText, { color: colors.danger }]}>
                  Delete item
                </Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {!editable && (
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.secondaryButton}
          >
            <Text style={styles.secondaryButtonText}>Back</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};
