import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { createItemStyles } from "../../styles/item";
import { createOutfitStyles } from "../../styles/outfit";
import { createOutfit, getMyOutfits, getOutfit, updateOutfit } from "../../api/outfits";
import { getAllRelatedWardrobes } from "../../api/wardrobes";
import { getMyItems, getWardrobeItems } from "../../api/items";
import { errorMessage } from "../../api/client";
import { Item } from "../../types/item";
import { Outfit, OutfitItem, OutfitItemRef } from "../../types/outfit";
import { Wardrobe } from "../../types/wardrobe";
import { Chip } from "../../components/ui/Chip";
import { OutfitCanvas } from "../../components/outfit/OutfitCanvas";
import { defaultLayout } from "../../utils/outfitLayout";
import { OutfitsStackParamList } from "../../navigation/OutfitsNavigator";

type Props = NativeStackScreenProps<OutfitsStackParamList, "OutfitForm">;

type Pickable = OutfitItemRef & { id: string };

export const OutfitFormScreen: React.FC<Props> = ({ route, navigation }) => {
  const { outfitId, wardrobeId: preselected } = route.params;
  const { token, user } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  const itemStyles = useMemo(() => createItemStyles(colors), [colors]);
  const outfitStyles = useMemo(() => createOutfitStyles(colors), [colors]);

  const [existing, setExisting] = useState<Outfit | null>(null);
  const [editableWardrobes, setEditableWardrobes] = useState<Wardrobe[]>([]);
  const [wardrobeId, setWardrobeId] = useState<string | null>(preselected ?? null);
  const [name, setName] = useState("");
  const [available, setAvailable] = useState<Item[] | null>(null);
  const [selected, setSelected] = useState<OutfitItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // load the outfit being edited + wardrobes I can create outfits in
  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        // fresh, not cached: wardrobes/roles may have changed on other devices
        const ws = await getAllRelatedWardrobes(token, { forceRefresh: true });
        setEditableWardrobes(
          ws.filter((w) => ["owner", "editor"].includes(w.roles[user?.id ?? ""]))
        );
        if (outfitId) {
          const cachedOutfit = (await getMyOutfits(token)).find((o) => o._id === outfitId);
          const o = cachedOutfit ?? (await getOutfit(token, outfitId));
          setExisting(o);
          setName(o.name);
          setWardrobeId(o.wardrobe_id ?? null);
          setSelected(o.items);
        }
      } catch (e) {
        setError(errorMessage(e, "Could not load the outfit."));
      }
    })();
  }, [token, outfitId, user?.id]);

  // items you can pick: the wardrobe's items, or your own for personal outfits
  useEffect(() => {
    if (!token) return;
    setAvailable(null);
    (wardrobeId ? getWardrobeItems(token, wardrobeId) : getMyItems(token))
      .then(setAvailable)
      .catch((e) => setError(errorMessage(e, "Could not load items.")));
  }, [token, wardrobeId]);

  // pickable = loaded items + items already in the outfit (a personal outfit
  // can hold items from wardrobes that aren't in "my items")
  const pickable: Pickable[] = useMemo(() => {
    const list: Pickable[] = (available ?? []).map((i) => ({
      id: i._id,
      name: i.name,
      categories: i.categories,
      image_url: i.image_url,
    }));
    for (const [id, ref] of Object.entries(existing?.item_refs ?? {})) {
      if (!list.some((p) => p.id === id)) list.push({ id, ...ref });
    }
    return list;
  }, [available, existing]);

  const refs = useMemo(
    () => Object.fromEntries(pickable.map(({ id, ...ref }) => [id, ref])),
    [pickable]
  );

  const toggle = (p: Pickable) =>
    setSelected((prev) => {
      if (prev.some((oi) => oi.item_id === p.id)) {
        return prev.filter((oi) => oi.item_id !== p.id);
      }
      // lay out with the already-selected items, so two tops sit side by side
      const asItems = [
        ...prev.map((oi) => ({ _id: oi.item_id, categories: refs[oi.item_id]?.categories ?? [] })),
        { _id: p.id, categories: p.categories },
      ] as Item[];
      return [...prev, defaultLayout(asItems)[asItems.length - 1]];
    });

  const chooseWardrobe = (id: string | null) => {
    if (id === wardrobeId) return;
    setWardrobeId(id);
    setSelected([]); // items are per wardrobe
  };

  const canSave = !busy && name.trim().length > 0 && selected.length > 0;

  const handleSave = async () => {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      if (existing) {
        await updateOutfit(token, existing._id, { name: name.trim(), items: selected });
        navigation.goBack();
      } else {
        const created = await createOutfit(token, {
          name: name.trim(),
          wardrobe_id: wardrobeId,
          items: selected,
        });
        navigation.replace("OutfitDetail", { outfitId: created._id });
      }
    } catch (e) {
      console.log("Failed to save outfit", e);
      setError(errorMessage(e, "Could not save the outfit. Please try again."));
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Text style={styles.title}>{existing ? "Edit outfit" : "New outfit"}</Text>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={[styles.sectionCard, styles.form]}>
          <OutfitCanvas items={selected} refs={refs} />

          <Text style={styles.metaLabel}>Name</Text>
          <TextInput
            value={name}
            onChangeText={setName}
            style={styles.input}
            placeholder="e.g. Friday office"
            placeholderTextColor={colors.textMuted}
          />

          <Text style={styles.metaLabel}>Wardrobe</Text>
          {existing ? (
            <Text style={styles.metaValue}>
              {existing.wardrobe_id
                ? editableWardrobes.find((w) => w._id === existing.wardrobe_id)?.name ??
                  "Wardrobe"
                : "Personal"}
            </Text>
          ) : (
            <View style={itemStyles.chipWrap}>
              <Chip
                label="Personal"
                selected={wardrobeId === null}
                onPress={() => chooseWardrobe(null)}
              />
              {editableWardrobes.map((w) => (
                <Chip
                  key={w._id}
                  label={w.name}
                  selected={wardrobeId === w._id}
                  onPress={() => chooseWardrobe(w._id)}
                />
              ))}
            </View>
          )}
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>
            Items ({selected.length} selected)
          </Text>
          {available === null ? (
            <ActivityIndicator color={colors.primarySoft} />
          ) : pickable.length === 0 ? (
            <Text style={itemStyles.empty}>
              {wardrobeId
                ? "This wardrobe has no items yet."
                : "You don't have any items yet. Add some in a wardrobe first."}
            </Text>
          ) : (
            <View style={outfitStyles.pickGrid}>
              {pickable.map((p) => {
                const isSelected = selected.some((oi) => oi.item_id === p.id);
                return (
                  <TouchableOpacity
                    key={p.id}
                    onPress={() => toggle(p)}
                    style={[outfitStyles.pickCell, isSelected && outfitStyles.pickCellSelected]}
                    accessibilityRole="checkbox"
                    accessibilityState={{ checked: isSelected }}
                    accessibilityLabel={p.name}
                  >
                    {p.image_url ? (
                      <Image
                        source={{ uri: p.image_url, cacheKey: p.image_url.split("?")[0] }}
                        style={itemStyles.imagePlaceholder}
                        contentFit="cover"
                      />
                    ) : (
                      <View style={itemStyles.imagePlaceholder}>
                        <Ionicons name="shirt-outline" size={28} color={colors.textMuted} />
                      </View>
                    )}
                    <Text style={outfitStyles.pickName} numberOfLines={1}>
                      {isSelected ? "✓ " : ""}
                      {p.name}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          )}
        </View>

        <View style={styles.buttonRow}>
          <TouchableOpacity
            onPress={handleSave}
            disabled={!canSave}
            style={[styles.primaryButton, { flex: 1 }, !canSave && styles.buttonDisabled]}
          >
            <Text style={styles.primaryButtonText}>{busy ? "Saving…" : "Save outfit"}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            disabled={busy}
            style={[styles.secondaryButton, { flex: 1 }]}
          >
            <Text style={styles.secondaryButtonText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};
