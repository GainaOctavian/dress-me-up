import React, { useEffect, useMemo, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  Alert,
  TextInput,
  Switch,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuth } from "../../hooks/useAuth";
import {
  getCurrentUser,
  updateCurrentUser,
  deleteCurrentUser,
} from "../../api/users";
import { User } from "../../types/user";
import { useTheme } from "../../hooks/useTheme";
import { createProfileStyles } from "../../styles/profile";

export const ProfileScreen: React.FC = () => {
  const { token, logout, setUser: setAuthUser } = useAuth();
  const { colors, mode, toggleTheme } = useTheme();

  const styles = useMemo(() => createProfileStyles(colors), [colors]);

  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const [editing, setEditing] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [isPrivate, setIsPrivate] = useState(true);
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");

  const [saving, setSaving] = useState(false);

  const loadUser = async () => {
    if (!token) return;

    setError("");
    setLoading(true);

    try {
      const response = await getCurrentUser(token);
      setUser(response.user);
      setEmail(response.user.email);
      setName(response.user.name ?? "");
      setIsPrivate(response.user.private_profile);
    } catch (err) {
      console.log("Failed to load current user:", err);
      setError("Could not load your profile.");
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    if (!token) return;
    setRefreshing(true);
    try {
      const response = await getCurrentUser(token);
      setUser(response.user);
      setEmail(response.user.email);
      setName(response.user.name ?? "");
      setIsPrivate(response.user.private_profile);
    } catch (err) {
      console.log("Failed to refresh current user:", err);
      setError("Could not refresh your profile.");
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, [token]);

  const startEdit = () => {
    if (!user) return;
    setEmail(user.email);
    setName(user.name ?? "");
    setIsPrivate(user.private_profile);
    setPassword("");
    setPasswordConfirm("");
    setError("");
    setEditing(true);
  };

  const validateForm = (): boolean => {
    const e = email.trim();

    if (!e) {
      setError("Email cannot be empty.");
      return false;
    }
    if (!e.includes("@")) {
      setError("Please enter a valid email.");
      return false;
    }

    if (password || passwordConfirm) {
      if (password.length < 6) {
        setError("Password must be at least 6 characters.");
        return false;
      }
      if (password !== passwordConfirm) {
        setError("Passwords do not match.");
        return false;
      }
    }

    return true;
  };

  const handleSave = async () => {
    if (!token || !user) return;

    setError("");
    if (!validateForm()) return;

    setSaving(true);
    try {
      const payload: any = {
        email: email.trim(),
        name: name.trim() || null,
        private_profile: isPrivate,
      };
      if (password) {
        payload.password = password;
      }

      const response = await updateCurrentUser(token, payload);
      setUser(response.user);
      setAuthUser(response.user);
      setEditing(false);
    } catch (err) {
      console.log("Failed to update user:", err);
      setError("Could not save your changes. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    if (!user) {
      setEditing(false);
      return;
    }
    setEmail(user.email);
    setName(user.name ?? "");
    setIsPrivate(user.private_profile);
    setPassword("");
    setPasswordConfirm("");
    setError("");
    setEditing(false);
  };

  const handleDelete = () => {
    Alert.alert(
      "Delete account",
      "Are you sure you want to delete your account? This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            if (!token) return;
            try {
              await deleteCurrentUser(token);
              logout();
            } catch (err) {
              console.log("Failed to delete user:", err);
              Alert.alert(
                "Error",
                "Could not delete your account. Please try again."
              );
            }
          },
        },
      ]
    );
  };

  if (loading && !refreshing) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primarySoft} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.primarySoft}
          />
        }
      >
        <View style={styles.header}>
          <Text style={styles.title}>Welcome to DressMeUp :3</Text>
          <Text style={styles.subtitle}>
            Your home after sign in. From here you get to your wardrobe,
            friends and generated outfits.
          </Text>
        </View>

        {/* Theme toggle */}
        <View style={styles.themeRow}>
          <View>
            <Text style={styles.themeTitle}>App theme</Text>
            <Text style={styles.themeSubtitle}>
              {mode === "dark" ? "Dark mode" : "Light mode"}
            </Text>
          </View>
          <Switch
            value={mode === "dark"}
            onValueChange={toggleTheme}
            trackColor={{ false: colors.border, true: colors.primarySoft }}
            thumbColor={"#fff"}
          />
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Profile</Text>
            {!editing && (
              <TouchableOpacity onPress={startEdit}>
                <Text style={styles.editLink}>Edit</Text>
              </TouchableOpacity>
            )}
          </View>

          {editing ? (
            <>
              <View style={styles.field}>
                <Text style={styles.label}>Email</Text>
                <TextInput
                  style={styles.input}
                  value={email}
                  onChangeText={setEmail}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />
              </View>

              <View style={styles.field}>
                <Text style={styles.label}>Name</Text>
                <TextInput
                  style={styles.input}
                  value={name}
                  onChangeText={setName}
                  placeholder="Display name"
                  placeholderTextColor={colors.textMuted}
                />
              </View>

              <View style={styles.fieldRow}>
                <Text style={styles.label}>Private profile</Text>
                <Switch
                  value={isPrivate}
                  onValueChange={setIsPrivate}
                  trackColor={{
                    false: colors.border,
                    true: colors.primarySoft,
                  }}
                  thumbColor={"#fff"}
                />
              </View>

              <View style={styles.field}>
                <Text style={styles.label}>New password (optional)</Text>
                <TextInput
                  style={styles.input}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  placeholder="Leave empty to keep the current one"
                  placeholderTextColor={colors.textMuted}
                />
              </View>

              <View style={styles.field}>
                <Text style={styles.label}>Confirm password</Text>
                <TextInput
                  style={styles.input}
                  value={passwordConfirm}
                  onChangeText={setPasswordConfirm}
                  secureTextEntry
                />
              </View>

              <View style={styles.editActions}>
                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={handleCancelEdit}
                  disabled={saving}
                >
                  <Text style={styles.secondaryText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.primaryButton}
                  onPress={handleSave}
                  disabled={saving}
                >
                  {saving ? (
                    <ActivityIndicator color={colors.buttonTextOnPrimary} />
                  ) : (
                    <Text style={styles.primaryText}>Save</Text>
                  )}
                </TouchableOpacity>
              </View>
            </>
          ) : (
            <>
              <View style={styles.row}>
                <Text style={styles.label}>Email</Text>
                <Text style={styles.value}>{user?.email}</Text>
              </View>

              <View style={styles.row}>
                <Text style={styles.label}>Name</Text>
                <Text style={styles.value}>{user?.name ?? "-"}</Text>
              </View>

              <View style={styles.row}>
                <Text style={styles.label}>Private profile</Text>
                <Text style={styles.value}>
                  {user?.private_profile ? "Yes" : "No"}
                </Text>
              </View>

              <View style={styles.row}>
                <Text style={styles.label}>Friends</Text>
                <Text style={styles.value}>
                  {user?.friend_ids?.length ?? 0}
                </Text>
              </View>
            </>
          )}
        </View>

        <View style={styles.actions}>
          <TouchableOpacity style={styles.bigPrimaryButton}>
            <Text style={styles.bigPrimaryText}>Open wardrobe</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryOutline} onPress={logout}>
            <Text style={styles.secondaryOutlineText}>Logout</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.dangerButton} onPress={handleDelete}>
            <Text style={styles.dangerText}>Delete account</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};
