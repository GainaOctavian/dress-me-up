import React, { useCallback, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
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
import { createOutfitStyles } from "../../styles/outfit";
import { getMyOutfits } from "../../api/outfits";
import { getAllRelatedWardrobes } from "../../api/wardrobes";
import { Outfit } from "../../types/outfit";
import { Wardrobe } from "../../types/wardrobe";
import { Chip } from "../../components/ui/Chip";
import { OutfitCanvas } from "../../components/outfit/OutfitCanvas";
import { OutfitsStackParamList } from "../../navigation/OutfitsNavigator";

type Props = NativeStackScreenProps<OutfitsStackParamList, "OutfitsList">;

// "all", "personal", or a wardrobe id
type Filter = string;

const OutfitsScreen: React.FC<Props> = ({ navigation }) => {
  const { token } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  const outfitStyles = useMemo(() => createOutfitStyles(colors), [colors]);

  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [wardrobes, setWardrobes] = useState<Wardrobe[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (forceRefresh = false) => {
      if (!token) return;
      try {
        setError(null);
        const [os, ws] = await Promise.all([
          getMyOutfits(token, { forceRefresh }),
          getAllRelatedWardrobes(token, { forceRefresh }),
        ]);
        setOutfits(os);
        setWardrobes(ws);
      } catch (e) {
        console.log("Failed to load outfits", e);
        setError("Could not load outfits. Please try again.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [token]
  );

  // cache-first on focus, so edits made in detail/form show up right away
  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  // item image URLs expire (~24h): refetch once per visit if one breaks
  const refetchedImages = useRef(false);
  const onImageError = () => {
    if (refetchedImages.current) return;
    refetchedImages.current = true;
    void load(true);
  };

  const wardrobeName = (id?: string | null) =>
    id ? wardrobes.find((w) => w._id === id)?.name ?? "Wardrobe" : "Personal";

  // only wardrobes that actually have outfits get a chip
  const usedWardrobes = wardrobes.filter((w) =>
    outfits.some((o) => o.wardrobe_id === w._id)
  );
  const visible = outfits.filter((o) =>
    filter === "all"
      ? true
      : filter === "personal"
        ? !o.wardrobe_id
        : o.wardrobe_id === filter
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.loaderContainer}>
          <ActivityIndicator size="large" color={colors.primarySoft} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <FlatList
        data={visible}
        keyExtractor={(o) => o._id}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              void load(true);
            }}
            tintColor={colors.primarySoft}
          />
        }
        contentContainerStyle={[
          styles.listContent,
          visible.length === 0 && { flexGrow: 1 },
        ]}
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.title}>Outfits</Text>
            <Text style={styles.subtitle}>
              Your outfits and the ones in your wardrobes.
            </Text>
            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            <View style={[styles.chipRow, { marginTop: 12, flexWrap: "wrap" }]}>
              <Chip label="All" selected={filter === "all"} onPress={() => setFilter("all")} />
              <Chip
                label="Personal"
                selected={filter === "personal"}
                onPress={() => setFilter("personal")}
              />
              {usedWardrobes.map((w) => (
                <Chip
                  key={w._id}
                  label={w.name}
                  selected={filter === w._id}
                  onPress={() => setFilter(w._id)}
                />
              ))}
              <TouchableOpacity
                onPress={() =>
                  navigation.navigate("OutfitForm", {
                    wardrobeId:
                      filter !== "all" && filter !== "personal" ? filter : null,
                  })
                }
                style={[styles.chip, { marginLeft: "auto" }]}
              >
                <Text style={styles.chipText}>+ New</Text>
              </TouchableOpacity>
            </View>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={outfitStyles.card}
            activeOpacity={0.85}
            onPress={() => navigation.navigate("OutfitDetail", { outfitId: item._id })}
          >
            <OutfitCanvas
              items={item.items}
              refs={item.item_refs}
              onImageError={onImageError}
              bodyId={item.body_id}
              poseId={item.pose_id}
            />
            <Text style={outfitStyles.cardTitle}>{item.name}</Text>
            <Text style={outfitStyles.cardMeta}>
              {wardrobeName(item.wardrobe_id)} · {item.items.length}{" "}
              {item.items.length === 1 ? "item" : "items"}
            </Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>No outfits yet</Text>
            <Text style={styles.emptyText}>
              Put together items from your wardrobes into an outfit.
            </Text>
            <TouchableOpacity
              onPress={() => navigation.navigate("OutfitForm", {})}
              style={[styles.primaryButton, { marginTop: 16, paddingHorizontal: 24 }]}
            >
              <Text style={styles.primaryButtonText}>Create outfit</Text>
            </TouchableOpacity>
          </View>
        }
      />
    </SafeAreaView>
  );
};

export default OutfitsScreen;
