import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  Text,
  TextInput,
  View,
  TouchableOpacity,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import {
  createWardrobe,
  getAllRelatedWardrobes,
  getOwnedWardrobes,
} from "../../api/wardrobes";
import { errorMessage } from "../../api/client";
import { Wardrobe } from "../../types/wardrobe";
import { WardrobeCard } from "../../components/wardrobe/WardrobeCard";
import { Chip } from "../../components/ui/Chip";
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

  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [query, setQuery] = useState("");

  const q = query.trim().toLowerCase();
  const visible = q
    ? wardrobes.filter((w) =>
        `${w.name} ${w.description ?? ""}`.toLowerCase().includes(q)
      )
    : wardrobes;

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

  const handleCreate = async () => {
    if (!token) return;
    setSaving(true);
    try {
      const wardrobe = await createWardrobe(token, {
        name: newName.trim(),
        description: newDescription.trim() || null,
      });
      setCreating(false);
      setNewName("");
      setNewDescription("");
      navigation.navigate("WardrobeDetail", { wardrobeId: wardrobe._id });
    } catch (e) {
      console.log("Failed to create wardrobe", e);
      setError(errorMessage(e, "Could not create wardrobe. Please try again."));
    } finally {
      setSaving(false);
    }
  };

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
        data={visible}
        keyExtractor={(item) => item._id}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primarySoft}
          />
        }
        contentContainerStyle={[
          styles.listContent,
          visible.length === 0 && { flexGrow: 1 },
        ]}
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.title}>Your wardrobes</Text>
            <Text style={styles.subtitle}>
              {filter === "owner"
                ? "Wardrobes you own."
                : "All wardrobes where you are owner, editor or viewer."}
            </Text>
            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            <View style={[styles.chipRow, { marginTop: 12 }]}>
              {FILTERS.map(({ key, label }) => (
                <Chip
                  key={key}
                  label={label}
                  selected={filter === key}
                  onPress={() => setFilter(key)}
                />
              ))}
              <TouchableOpacity
                onPress={() => setCreating((v) => !v)}
                style={[styles.chip, { marginLeft: "auto" }]}
              >
                <Text style={styles.chipText}>
                  {creating ? "Close" : "+ New"}
                </Text>
              </TouchableOpacity>
            </View>

            {wardrobes.length > 0 && !creating && (
              <TextInput
                value={query}
                onChangeText={setQuery}
                style={[styles.input, { marginTop: 12 }]}
                placeholder="Search wardrobes"
                placeholderTextColor={colors.textMuted}
                autoCorrect={false}
              />
            )}

            {creating && (
              <View style={[styles.sectionCard, styles.form, { marginTop: 12 }]}>
                <TextInput
                  value={newName}
                  onChangeText={setNewName}
                  style={styles.input}
                  placeholder="Wardrobe name"
                  placeholderTextColor={colors.textMuted}
                />
                <TextInput
                  value={newDescription}
                  onChangeText={setNewDescription}
                  multiline
                  style={[styles.input, styles.inputMultiline]}
                  placeholder="Description (optional)"
                  placeholderTextColor={colors.textMuted}
                />
                <TouchableOpacity
                  onPress={handleCreate}
                  disabled={saving || !newName.trim()}
                  style={[
                    styles.primaryButton,
                    (saving || !newName.trim()) && styles.buttonDisabled,
                  ]}
                >
                  <Text style={styles.primaryButtonText}>
                    {saving ? "Creating…" : "Create wardrobe"}
                  </Text>
                </TouchableOpacity>
              </View>
            )}
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
          q ? (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>No wardrobes match "{query}".</Text>
            </View>
          ) : (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyTitle}>No wardrobes yet</Text>
              <Text style={styles.emptyText}>
                Create one, or ask a friend to add you to theirs.
              </Text>
              {!creating && (
                <TouchableOpacity
                  onPress={() => setCreating(true)}
                  style={[styles.primaryButton, { marginTop: 16, paddingHorizontal: 24 }]}
                >
                  <Text style={styles.primaryButtonText}>Create wardrobe</Text>
                </TouchableOpacity>
              )}
            </View>
          )
        }
      />
    </SafeAreaView>
  );
};

export default WardrobeScreen;
