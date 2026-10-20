import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  Text,
  View,
  TouchableOpacity,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { getAllRelatedWardrobes, getOwnedWardrobes } from "../../api/wardrobes";
import { Wardrobe } from "../../types/wardrobe";
import { WardrobeCard } from "../../components/wardrobe/WardrobeCard";
import { WardrobeStackParamList } from "../../navigation/WardrobeNavigator";

type Props = NativeStackScreenProps<WardrobeStackParamList, "WardrobeList">;

type WardrobeFilter = "all" | "owner";

const FILTERS: { key: WardrobeFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "owner", label: "My wardrobes" },
];

const WardrobeScreen: React.FC<Props> = ({ navigation }) => {
  const { token, user } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);

  const [filter, setFilter] = useState<WardrobeFilter>("all");
  const [wardrobes, setWardrobes] = useState<Wardrobe[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (forceRefresh = false) => {
      if (!token) return;
      try {
        setError(null);
        const fetchWardrobes =
          filter === "owner" ? getOwnedWardrobes : getAllRelatedWardrobes;
        setWardrobes(await fetchWardrobes(token, { forceRefresh }));
      } catch (e) {
        console.log("Failed to load wardrobes", e);
        setError("Could not load wardrobes. Please try again.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [token, filter]
  );

  // Runs on focus and on filter change. Cache-first, so coming back from
  // the detail screen picks up its edits without a GET.
  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  const onRefresh = () => {
    setRefreshing(true);
    void load(true);
  };

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
        data={wardrobes}
        keyExtractor={(item) => item._id}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primarySoft}
          />
        }
        contentContainerStyle={[
          styles.listContent,
          wardrobes.length === 0 && { flexGrow: 1 },
        ]}
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.title}>Your wardrobes</Text>
            <Text style={styles.subtitle}>
              All wardrobes where you are owner, editor or viewer.
            </Text>
            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            <View style={[styles.chipRow, { marginTop: 12 }]}>
              {FILTERS.map(({ key, label }) => (
                <TouchableOpacity
                  key={key}
                  onPress={() => setFilter(key)}
                  style={[styles.chip, filter !== key && styles.chipInactive]}
                >
                  <Text
                    style={[
                      styles.chipText,
                      filter !== key && styles.chipTextInactive,
                    ]}
                  >
                    {label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        }
        renderItem={({ item }) => (
          <WardrobeCard
            wardrobe={item}
            currentUserId={user?.id}
            onPress={() =>
              navigation.navigate("WardrobeDetail", { wardrobeId: item._id })
            }
          />
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>No wardrobes yet</Text>
            <Text style={styles.emptyText}>
              You are not part of any wardrobe yet. Later you will be able to
              create or join wardrobes from here.
            </Text>
          </View>
        }
      />
    </SafeAreaView>
  );
};

export default WardrobeScreen;
