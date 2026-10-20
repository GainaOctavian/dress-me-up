import React, { useEffect, useMemo, useState } from "react";
import {
  View,
  Text,
  ActivityIndicator,
  ScrollView,
  TextInput,
  TouchableOpacity,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import {
  getWardrobeById,
  updateWardrobe,
  addUserByEmailToWardrobe,
  removeUserFromWardrobe,
} from "../../api/wardrobes";
import { getUserById } from "../../api/users";
import { Wardrobe, WardrobeRole } from "../../types/wardrobe";
import { WardrobeStackParamList } from "../../navigation/WardrobeNavigator";

type Props = NativeStackScreenProps<WardrobeStackParamList, "WardrobeDetail">;

const ROLES: WardrobeRole[] = ["viewer", "editor", "owner"];

// apiClient throws Error(responseText); FastAPI sends {"detail": "..."}
const errorDetail = (e: unknown, fallback: string): string => {
  try {
    const detail = JSON.parse((e as Error).message).detail;
    return typeof detail === "string" ? detail : fallback;
  } catch {
    return fallback;
  }
};

export const WardrobeDetailScreen: React.FC<Props> = ({ route }) => {
  const { wardrobeId } = route.params;
  const { token, user: authUser } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);

  const [wardrobe, setWardrobe] = useState<Wardrobe | null>(null);
  const [memberNames, setMemberNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<WardrobeRole>("viewer");

  useEffect(() => {
    if (!token) return;
    getWardrobeById(token, wardrobeId)
      .then(setWardrobe)
      .catch((e) => {
        console.log("Failed to load wardrobe detail", e);
        setError("Could not load wardrobe. Please try again.");
      })
      .finally(() => setLoading(false));
  }, [token, wardrobeId]);

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
      setError(errorDetail(e, fallbackError));
      return false;
    } finally {
      setBusy(false);
    }
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

  if (!wardrobe) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.container}>
          <Text style={styles.errorText}>{error ?? "Wardrobe not found."}</Text>
        </View>
      </SafeAreaView>
    );
  }

  const myRole = authUser?.id ? wardrobe.roles[authUser.id] : undefined;
  const isOwner = myRole === "owner";
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

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
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

        {/* MEMBERS */}
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Members</Text>

          {Object.entries(wardrobe.roles).map(([memberId, role]) => (
            <View key={memberId} style={styles.memberRow}>
              <View>
                <Text style={styles.memberName}>{displayName(memberId)}</Text>
                <Text style={styles.memberSubtitle}>{role.toUpperCase()}</Text>
              </View>

              {isOwner && memberId !== authUser?.id && (
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
          ))}

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
                  <TouchableOpacity
                    key={role}
                    onPress={() => setNewMemberRole(role)}
                    style={[
                      styles.chip,
                      newMemberRole !== role && styles.chipInactive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.chipText,
                        newMemberRole !== role && styles.chipTextInactive,
                      ]}
                    >
                      {role.toUpperCase()}
                    </Text>
                  </TouchableOpacity>
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
      </ScrollView>
    </SafeAreaView>
  );
};
