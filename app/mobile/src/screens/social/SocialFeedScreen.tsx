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
import { getFeed } from "../../api/friends";
import { errorMessage } from "../../api/client";
import { Outfit } from "../../types/outfit";
import { PublicUser, displayName } from "../../types/friend";
import { OutfitCanvas } from "../../components/outfit/OutfitCanvas";
import { SocialStackParamList } from "../../navigation/SocialNavigator";

type Props = NativeStackScreenProps<SocialStackParamList, "Feed">;

// Plan 08: outfits friends shared, newest first. Never cached.
const SocialFeedScreen: React.FC<Props> = ({ navigation }) => {
  const { token } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  const outfitStyles = useMemo(() => createOutfitStyles(colors), [colors]);

  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [owners, setOwners] = useState<Record<string, PublicUser>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const more = useRef(true); // false once a page comes back short
  const fetching = useRef(false);

  const load = useCallback(
    async (append: boolean) => {
      if (!token || fetching.current || (append && !more.current)) return;
      fetching.current = true;
      try {
        setError(null);
        const before = append ? outfits[outfits.length - 1]?.created_at : undefined;
        const page = await getFeed(token, before);
        more.current = page.outfits.length === 20;
        setOutfits((prev) => (append ? [...prev, ...page.outfits] : page.outfits));
        setOwners((prev) => ({ ...prev, ...page.owners }));
      } catch (e) {
        setError(errorMessage(e, "Could not load the feed."));
      } finally {
        fetching.current = false;
        setLoading(false);
        setRefreshing(false);
      }
    },
    [token, outfits]
  );

  useFocusEffect(
    useCallback(() => {
      more.current = true;
      void load(false);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token])
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
        data={outfits}
        keyExtractor={(o) => o._id}
        onEndReached={() => void load(true)}
        onEndReachedThreshold={0.5}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              more.current = true;
              void load(false);
            }}
            tintColor={colors.primarySoft}
          />
        }
        contentContainerStyle={[styles.listContent, outfits.length === 0 && { flexGrow: 1 }]}
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.memberRow}>
              <Text style={styles.title}>Feed</Text>
              <TouchableOpacity onPress={() => navigation.navigate("Friends")} style={styles.chip}>
                <Text style={styles.chipText}>Friends</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.subtitle}>Outfits your friends shared.</Text>
            {error ? <Text style={styles.errorText}>{error}</Text> : null}
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={outfitStyles.card}
            activeOpacity={0.85}
            disabled={!item.model_url}
            onPress={() =>
              item.model_url && navigation.navigate("Outfit3D", { modelUrl: item.model_url, name: item.name })
            }
          >
            <OutfitCanvas
              items={item.items}
              refs={item.item_refs}
              bodyId={item.body_id}
              poseId={item.pose_id}
              render={item.render}
              renderUrl={item.render_url}
            />
            <Text style={outfitStyles.cardTitle}>{item.name}</Text>
            <Text style={outfitStyles.cardMeta}>
              {displayName(owners[item.owner_id])} ·{" "}
              {new Date(item.created_at).toLocaleDateString()}
              {item.model_url ? " · tap to view in 3D" : ""}
            </Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>Nothing here yet</Text>
            <Text style={styles.emptyText}>
              Add friends, and their shared outfits show up here. Share yours from an
              outfit's page.
            </Text>
            <TouchableOpacity
              onPress={() => navigation.navigate("Friends")}
              style={[styles.primaryButton, { marginTop: 16, paddingHorizontal: 24 }]}
            >
              <Text style={styles.primaryButtonText}>Find friends</Text>
            </TouchableOpacity>
          </View>
        }
      />
    </SafeAreaView>
  );
};

export default SocialFeedScreen;
