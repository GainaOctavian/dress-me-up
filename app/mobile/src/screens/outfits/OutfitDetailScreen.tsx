import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { deleteOutfit, getMyOutfits, getOutfit } from "../../api/outfits";
import { getAllRelatedWardrobes } from "../../api/wardrobes";
import { errorMessage } from "../../api/client";
import { Outfit } from "../../types/outfit";
import { Wardrobe } from "../../types/wardrobe";
import { OutfitCanvas } from "../../components/outfit/OutfitCanvas";
import { confirmDestructive } from "../../utils/confirm";
import { OutfitsStackParamList } from "../../navigation/OutfitsNavigator";

type Props = NativeStackScreenProps<OutfitsStackParamList, "OutfitDetail">;

export const OutfitDetailScreen: React.FC<Props> = ({ route, navigation }) => {
  const { outfitId } = route.params;
  const { token, user } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);

  const [outfit, setOutfit] = useState<Outfit | null>(null);
  const [wardrobe, setWardrobe] = useState<Wardrobe | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (forceRefresh = false) => {
      if (!token) return;
      try {
        const cachedOutfit = forceRefresh
          ? undefined
          : (await getMyOutfits(token)).find((o) => o._id === outfitId);
        const o = cachedOutfit ?? (await getOutfit(token, outfitId));
        setOutfit(o);
        if (o.wardrobe_id) {
          const ws = await getAllRelatedWardrobes(token);
          setWardrobe(ws.find((w) => w._id === o.wardrobe_id) ?? null);
        }
      } catch (e) {
        setError(errorMessage(e, "Could not load the outfit."));
      }
    },
    [token, outfitId]
  );

  // re-read on focus: picks up edits made in the form
  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  // a 3D render is on its way: check back until it lands (~15 s per render)
  useEffect(() => {
    if (!token || outfit?.render?.status !== "queued") return;
    const timer = setTimeout(() => {
      getOutfit(token, outfitId).then(setOutfit).catch(() => {});
    }, 4000);
    return () => clearTimeout(timer);
  }, [token, outfitId, outfit]);

  const refetchedImages = useRef(false);
  const onImageError = () => {
    if (refetchedImages.current) return;
    refetchedImages.current = true;
    void load(true);
  };

  if (!outfit) {
    return (
      <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
        <View style={styles.loaderContainer}>
          {error ? (
            <Text style={styles.errorText}>{error}</Text>
          ) : (
            <ActivityIndicator size="large" color={colors.primarySoft} />
          )}
        </View>
      </SafeAreaView>
    );
  }

  // same rule as the backend: wardrobe editors/owners, or the owner of a
  // personal outfit
  const myRole = wardrobe && user?.id ? wardrobe.roles[user.id] : undefined;
  const canEdit = outfit.wardrobe_id
    ? myRole === "owner" || myRole === "editor"
    : outfit.owner_id === user?.id;
  const missing = outfit.items.length - Object.keys(outfit.item_refs).length;

  const handleDelete = async () => {
    if (!token) return;
    const ok = await confirmDestructive(
      "Delete outfit",
      `Delete "${outfit.name}"? The items themselves are kept.`
    );
    if (!ok) return;
    setBusy(true);
    try {
      await deleteOutfit(token, outfit._id);
      navigation.goBack();
    } catch (e) {
      setError(errorMessage(e, "Could not delete the outfit. Please try again."));
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.title}>{outfit.name}</Text>
          <Text style={styles.subtitle}>
            {outfit.wardrobe_id ? wardrobe?.name ?? "Wardrobe" : "Personal outfit"} ·{" "}
            {new Date(outfit.created_at).toLocaleDateString()}
          </Text>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={styles.sectionCard}>
          <OutfitCanvas
            items={outfit.items}
            refs={outfit.item_refs}
            onImageError={onImageError}
            bodyId={outfit.body_id}
            poseId={outfit.pose_id}
            render={outfit.render}
            renderUrl={outfit.render_url}
          />
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Items</Text>
          {outfit.items.map((oi) => {
            const ref = outfit.item_refs[oi.item_id];
            if (!ref) return null;
            return (
              <View key={oi.item_id} style={styles.memberRow}>
                <Text style={styles.memberName}>{ref.name}</Text>
                <Text style={styles.memberSubtitle}>{ref.categories.join(" · ")}</Text>
              </View>
            );
          })}
          {missing > 0 && (
            <Text style={[styles.memberSubtitle, { marginTop: 8 }]}>
              {missing} item{missing === 1 ? " was" : "s were"} deleted.
            </Text>
          )}
        </View>

        {canEdit && (
          <View style={[styles.form, { marginBottom: 10 }]}>
            <TouchableOpacity
              onPress={() => navigation.navigate("OutfitForm", { outfitId: outfit._id })}
              disabled={busy}
              style={styles.primaryButton}
            >
              <Text style={styles.primaryButtonText}>Edit outfit</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={handleDelete}
              disabled={busy}
              style={styles.secondaryButton}
            >
              <Text style={[styles.secondaryButtonText, { color: colors.danger }]}>
                Delete outfit
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};
