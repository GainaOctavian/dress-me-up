import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  View,
  Text,
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  TextInput,
  TouchableOpacity,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useFocusEffect } from "@react-navigation/native";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { createItemStyles } from "../../styles/item";
import {
  getWardrobeById,
  updateWardrobe,
  addUserByEmailToWardrobe,
  removeUserFromWardrobe,
  deleteWardrobe,
  leaveWardrobe,
  setMemberRole,
  storeWardrobe,
} from "../../api/wardrobes";
import { getUserById } from "../../api/users";
import { getWardrobeItems } from "../../api/items";
import { errorMessage } from "../../api/client";
import { Wardrobe, WardrobeRole } from "../../types/wardrobe";
import { Item, ItemCategory } from "../../types/item";
import { Chip } from "../../components/ui/Chip";
import { confirmDestructive } from "../../utils/confirm";
import { ItemCard } from "../../components/item/ItemCard";
import { WardrobeStackParamList } from "../../navigation/WardrobeNavigator";

type Props = NativeStackScreenProps<WardrobeStackParamList, "WardrobeDetail">;

const ROLES: WardrobeRole[] = ["viewer", "editor", "owner"];

export const WardrobeDetailScreen: React.FC<Props> = ({
  route,
  navigation,
}) => {
  const { wardrobeId } = route.params;
  const { token, user: authUser } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  const itemStyles = useMemo(() => createItemStyles(colors), [colors]);

  const [wardrobe, setWardrobe] = useState<Wardrobe | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<ItemCategory | null>(
    null
  );
  const [refreshing, setRefreshing] = useState(false);
  const [memberNames, setMemberNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<WardrobeRole>("viewer");

  const load = useCallback(
    async (forceRefresh = false) => {
      if (!token) return;
      try {
        const [w, its] = await Promise.all([
          getWardrobeById(token, wardrobeId, { forceRefresh }),
          getWardrobeItems(token, wardrobeId, { forceRefresh }),
        ]);
        setWardrobe(w);
        setItems(its);
        // keep the list card's item count in sync without refetching the list
        if (w.item_count !== its.length) {
          void storeWardrobe({ ...w, item_count: its.length });
        }
      } catch (e) {
        console.log("Failed to load wardrobe detail", e);
        setError("Could not load wardrobe. Please try again.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [token, wardrobeId]
  );

  // Cache-first, so returning from ItemForm shows its changes without a GET.
  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  // While the worker processes photos, refetch every 4s (max ~2 min) so the
  // cutout and auto-filled tags/colors show up without pull-to-refresh.
  const processing = items.some(
    (i) => i.image_status === "ready" || i.image_status === "processing"
  );
  const polls = useRef(0);
  useEffect(() => {
    if (!processing || polls.current >= 30) return;
    const t = setTimeout(() => {
      polls.current += 1;
      void load(true);
    }, 4000);
    return () => clearTimeout(t);
  }, [processing, items, load]);

  // Cached items carry presigned image URLs that expire after ~24h.
  // The first broken image triggers one fresh fetch per visit.
  const refetchedImages = useRef(false);
  const onImageError = () => {
    if (refetchedImages.current) return;
    refetchedImages.current = true;
    void load(true);
  };

  const onRefresh = () => {
    setRefreshing(true);
    void load(true);
  };

  // Resolve member names; getUserById is cached, so re-running after
  // each membership change only hits the API for new members.
  useEffect(() => {
    if (!token || !wardrobe) return;
    Promise.all(
      Object.keys(wardrobe.roles).map((id) =>
        getUserById(token, id)
          .then((u) => [id, u.name || u.email] as const)
          .catch(() => [id, "Unknown user"] as const)
      )
    ).then((entries) => setMemberNames(Object.fromEntries(entries)));
  }, [token, wardrobe]);

  // Runs a mutation that returns the updated wardrobe; true on success.
  const mutate = async (
    action: (token: string) => Promise<Wardrobe>,
    fallbackError: string
  ): Promise<boolean> => {
    if (!token) return false;
    setBusy(true);
    try {
      setWardrobe(await action(token));
      setError(null);
      return true;
    } catch (e) {
      console.log(fallbackError, e);
      setError(errorMessage(e, fallbackError));
      return false;
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
        <View style={styles.loaderContainer}>
          <ActivityIndicator size="large" color={colors.primarySoft} />
        </View>
      </SafeAreaView>
    );
  }

  if (!wardrobe) {
    return (
      <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
        <View style={styles.container}>
          <Text style={styles.errorText}>{error ?? "Wardrobe not found."}</Text>
        </View>
      </SafeAreaView>
    );
  }

  const myRole = authUser?.id ? wardrobe.roles[authUser.id] : undefined;
  const isOwner = myRole === "owner";
  const canEditItems = myRole === "owner" || myRole === "editor";
  const ownerCount = Object.values(wardrobe.roles).filter(
    (r) => r === "owner"
  ).length;
  // the last owner can't leave (backend rule); they delete instead
  const canLeave = !!myRole && !(isOwner && ownerCount === 1);

  const presentCategories = [...new Set(items.flatMap((i) => i.categories))];
  const visibleItems = categoryFilter
    ? items.filter((i) => i.categories.includes(categoryFilter))
    : items;
  const displayName = (id: string) =>
    id === authUser?.id ? "You" : memberNames[id] ?? "…";

  const startEdit = () => {
    setName(wardrobe.name);
    setDescription(wardrobe.description ?? "");
    setIsEditing(true);
  };

  const handleSave = async () => {
    const ok = await mutate(
      (t) =>
        updateWardrobe(t, wardrobe._id, {
          name: name.trim(),
          description: description.trim() || null,
        }),
      "Could not update wardrobe. Please try again."
    );
    if (ok) setIsEditing(false);
  };

  const handleAddMember = async () => {
    const ok = await mutate(
      (t) =>
        addUserByEmailToWardrobe(
          t,
          wardrobe._id,
          newMemberEmail.trim(),
          newMemberRole
        ),
      "Could not add member. Please try again."
    );
    if (ok) {
      setNewMemberEmail("");
      setNewMemberRole("viewer");
    }
  };

  const handleRemoveMember = (memberId: string) =>
    mutate(
      (t) => removeUserFromWardrobe(t, wardrobe._id, memberId),
      "Could not remove member. Please try again."
    );

  const handleChangeRole = (memberId: string, role: WardrobeRole) =>
    mutate(
      (t) => setMemberRole(t, wardrobe._id, memberId, role),
      "Could not change role. Please try again."
    );

  // Confirm, run, then leave the screen (the wardrobe is gone for us).
  const exitAfter = async (
    title: string,
    message: string,
    confirmText: string,
    action: (token: string) => Promise<void>,
    fallbackError: string
  ) => {
    if (!token || !(await confirmDestructive(title, message, confirmText))) {
      return;
    }
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

  const handleDeleteWardrobe = () =>
    exitAfter(
      "Delete wardrobe",
      `Delete "${wardrobe.name}"? Its items are kept and stay in your other wardrobes.`,
      "Delete",
      (t) => deleteWardrobe(t, wardrobe._id),
      "Could not delete wardrobe. Please try again."
    );

  const handleLeave = () =>
    exitAfter(
      "Leave wardrobe",
      `Leave "${wardrobe.name}"? An owner will have to add you again.`,
      "Leave",
      (t) => leaveWardrobe(t, wardrobe._id),
      "Could not leave wardrobe. Please try again."
    );

  return (
    <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primarySoft}
          />
        }
      >
        <View style={styles.header}>
          <Text style={styles.title}>{wardrobe.name}</Text>
          <Text style={styles.subtitle}>
            {wardrobe.description || "No description provided."}
          </Text>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        {/* INFO / EDIT */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Info</Text>

          {isEditing ? (
            <View style={styles.form}>
              <Text style={styles.metaLabel}>Name</Text>
              <TextInput
                value={name}
                onChangeText={setName}
                style={styles.input}
                placeholder="Wardrobe name"
                placeholderTextColor={colors.textMuted}
              />

              <Text style={styles.metaLabel}>Description</Text>
              <TextInput
                value={description}
                onChangeText={setDescription}
                multiline
                style={[styles.input, styles.inputMultiline]}
                placeholder="Describe this wardrobe"
                placeholderTextColor={colors.textMuted}
              />

              <View style={styles.buttonRow}>
                <TouchableOpacity
                  onPress={handleSave}
                  disabled={busy || !name.trim()}
                  style={[
                    styles.primaryButton,
                    { flex: 1 },
                    (busy || !name.trim()) && styles.buttonDisabled,
                  ]}
                >
                  <Text style={styles.primaryButtonText}>
                    {busy ? "Saving…" : "Save"}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => setIsEditing(false)}
                  disabled={busy}
                  style={[styles.secondaryButton, { flex: 1 }]}
                >
                  <Text style={styles.secondaryButtonText}>Cancel</Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <>
              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Owner</Text>
                <Text style={styles.metaValue}>
                  {displayName(wardrobe.user_id)}
                </Text>
              </View>

              <View style={styles.metaRow}>
                <Text style={styles.metaLabel}>Created</Text>
                <Text style={styles.metaValue}>
                  {new Date(wardrobe.created_at).toLocaleString()}
                </Text>
              </View>

              {myRole && (
                <View style={[styles.metaRow, { marginTop: 12 }]}>
                  <Text style={styles.metaLabel}>Your role</Text>
                  <View style={styles.chip}>
                    <Text style={styles.chipText}>{myRole.toUpperCase()}</Text>
                  </View>
                </View>
              )}

              {isOwner && (
                <TouchableOpacity
                  onPress={startEdit}
                  style={[styles.primaryButton, { marginTop: 16 }]}
                >
                  <Text style={styles.primaryButtonText}>Edit wardrobe</Text>
                </TouchableOpacity>
              )}
            </>
          )}
        </View>

        {/* ITEMS */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Items ({items.length})</Text>

          {presentCategories.length > 1 && (
            <View style={[itemStyles.chipWrap, { marginBottom: 12 }]}>
              <Chip
                label="ALL"
                selected={categoryFilter === null}
                onPress={() => setCategoryFilter(null)}
              />
              {presentCategories.map((c) => (
                <Chip
                  key={c}
                  label={c.toUpperCase()}
                  selected={categoryFilter === c}
                  onPress={() => setCategoryFilter(c)}
                />
              ))}
            </View>
          )}

          {items.length === 0 ? (
            <Text style={itemStyles.empty}>No items in this wardrobe yet.</Text>
          ) : (
            <View style={itemStyles.grid}>
              {visibleItems.map((item) => (
                <ItemCard
                  key={item._id}
                  item={item}
                  onImageError={onImageError}
                  // owner edits; everyone else gets a read-only view
                  onPress={() =>
                    navigation.navigate("ItemForm", {
                      wardrobeId,
                      item,
                      canRemove: canEditItems || item.owner_id === authUser?.id,
                    })
                  }
                />
              ))}
            </View>
          )}

          {canEditItems && (
            <View style={styles.buttonRow}>
              <TouchableOpacity
                onPress={() => navigation.navigate("ItemForm", { wardrobeId })}
                style={[styles.primaryButton, { flex: 1, marginTop: 10 }]}
              >
                <Text style={styles.primaryButtonText}>New item</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() =>
                  navigation.navigate("AddExistingItems", { wardrobeId })
                }
                style={[styles.secondaryButton, { flex: 1, marginTop: 10 }]}
              >
                <Text style={styles.secondaryButtonText}>From my items</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* MEMBERS */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Members</Text>

          {Object.entries(wardrobe.roles).map(([memberId, role]) => {
            const manageable = isOwner && memberId !== authUser?.id;
            return (
              <View key={memberId} style={{ marginTop: 10 }}>
                <View style={styles.memberRow}>
                  <View>
                    <Text style={styles.memberName}>{displayName(memberId)}</Text>
                    <Text style={styles.memberSubtitle}>{role.toUpperCase()}</Text>
                  </View>

                  {manageable && (
                    <TouchableOpacity
                      onPress={() => handleRemoveMember(memberId)}
                      disabled={busy}
                      style={[styles.chip, styles.chipInactive]}
                    >
                      <Text style={[styles.chipText, { color: colors.danger }]}>
                        Remove
                      </Text>
                    </TouchableOpacity>
                  )}
                </View>

                {manageable && (
                  <View style={[styles.chipRow, { marginTop: 6 }]}>
                    {ROLES.map((r) => (
                      <Chip
                        key={r}
                        label={r.toUpperCase()}
                        selected={role === r}
                        disabled={busy}
                        onPress={
                          role === r
                            ? undefined
                            : () => handleChangeRole(memberId, r)
                        }
                      />
                    ))}
                  </View>
                )}
              </View>
            );
          })}

          {isOwner && (
            <View style={[styles.form, { marginTop: 16 }]}>
              <Text style={styles.metaLabel}>Add member by email</Text>
              <TextInput
                value={newMemberEmail}
                onChangeText={setNewMemberEmail}
                style={styles.input}
                placeholder="friend@example.com"
                placeholderTextColor={colors.textMuted}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
              />

              <View style={styles.chipRow}>
                {ROLES.map((role) => (
                  <Chip
                    key={role}
                    label={role.toUpperCase()}
                    selected={newMemberRole === role}
                    onPress={() => setNewMemberRole(role)}
                  />
                ))}
              </View>

              <TouchableOpacity
                onPress={handleAddMember}
                disabled={busy || !newMemberEmail.trim()}
                style={[
                  styles.primaryButton,
                  { marginTop: 6 },
                  (busy || !newMemberEmail.trim()) && styles.buttonDisabled,
                ]}
              >
                <Text style={styles.primaryButtonText}>
                  {busy ? "Saving…" : "Add member"}
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
        {canLeave && (
          <TouchableOpacity
            onPress={handleLeave}
            disabled={busy}
            style={[styles.secondaryButton, { marginBottom: 10 }]}
          >
            <Text style={styles.secondaryButtonText}>Leave wardrobe</Text>
          </TouchableOpacity>
        )}
        {isOwner && (
          <TouchableOpacity
            onPress={handleDeleteWardrobe}
            disabled={busy}
            style={styles.secondaryButton}
          >
            <Text style={[styles.secondaryButtonText, { color: colors.danger }]}>
              Delete wardrobe
            </Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};
