import React, { useMemo, useState } from "react";
import {
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

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
  const [tags, setTags] = useState(item?.tags.join(", ") ?? "");
  const [itemColors, setItemColors] = useState(item?.colors.join(", ") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleCategory = (c: ItemCategory) =>
    setCategories((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
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
      tags: parseList(tags),
      colors: parseList(itemColors),
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

  const canSave = !busy && name.trim().length > 0;

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
                {busy ? "Saving…" : "Save"}
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
