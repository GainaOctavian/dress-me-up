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
  const { token, logout } = useAuth();
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
      setError("Nu am putut încărca datele profilului.");
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
      setError("Eroare la refresh.");
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
      setError("Email-ul nu poate fi gol.");
      return false;
    }
    if (!e.includes("@")) {
      setError("Te rog introdu un email valid.");
      return false;
    }

    if (password || passwordConfirm) {
      if (password.length < 6) {
        setError("Parola trebuie să aibă cel puțin 6 caractere.");
        return false;
      }
      if (password !== passwordConfirm) {
        setError("Parolele nu coincid.");
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
      setEditing(false);
    } catch (err) {
      console.log("Failed to update user:", err);
      setError("Nu am putut salva modificările. Încearcă din nou.");
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
      "Ștergere cont",
      "Ești sigur că vrei să-ți ștergi contul? Acțiunea este permanentă.",
      [
        { text: "Anulează", style: "cancel" },
        {
          text: "Șterge",
          style: "destructive",
          onPress: async () => {
            if (!token) return;
            try {
              await deleteCurrentUser(token);
              logout();
            } catch (err) {
              console.log("Failed to delete user:", err);
              Alert.alert(
                "Eroare",
                "Nu am putut șterge contul. Te rog încearcă din nou."
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
          <Text style={styles.title}>Bine ai venit în DressMeUp :3</Text>
          <Text style={styles.subtitle}>
            Asta e landing page-ul după login. De aici intri în garderobă,
            prieteni și outfit-uri generate.
          </Text>
        </View>

        {/* Theme toggle */}
        <View style={styles.themeRow}>
          <View>
            <Text style={styles.themeTitle}>Tema aplicației</Text>
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
            <Text style={styles.cardTitle}>Profil</Text>
            {!editing && (
              <TouchableOpacity onPress={startEdit}>
                <Text style={styles.editLink}>Editează</Text>
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
                <Text style={styles.label}>Nume</Text>
                <TextInput
                  style={styles.input}
                  value={name}
                  onChangeText={setName}
                  placeholder="Nume afișat"
                  placeholderTextColor={colors.textMuted}
                />
              </View>

              <View style={styles.fieldRow}>
                <Text style={styles.label}>Profil privat</Text>
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
                <Text style={styles.label}>Parolă nouă (opțional)</Text>
                <TextInput
                  style={styles.input}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                  placeholder="Lasă gol dacă nu vrei să o schimbi"
                  placeholderTextColor={colors.textMuted}
                />
              </View>

              <View style={styles.field}>
                <Text style={styles.label}>Confirmare parolă</Text>
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
                  <Text style={styles.secondaryText}>Renunță</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.primaryButton}
                  onPress={handleSave}
                  disabled={saving}
                >
                  {saving ? (
                    <ActivityIndicator color={colors.buttonTextOnPrimary} />
                  ) : (
                    <Text style={styles.primaryText}>Salvează</Text>
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
                <Text style={styles.label}>Nume</Text>
                <Text style={styles.value}>{user?.name ?? "-"}</Text>
              </View>

              <View style={styles.row}>
                <Text style={styles.label}>Profil privat</Text>
                <Text style={styles.value}>
                  {user?.private_profile ? "Da" : "Nu"}
                </Text>
              </View>

              <View style={styles.row}>
                <Text style={styles.label}>Prieteni</Text>
                <Text style={styles.value}>
                  {user?.friend_ids?.length ?? 0}
                </Text>
              </View>
            </>
          )}
        </View>

        <View style={styles.actions}>
          <TouchableOpacity style={styles.bigPrimaryButton}>
            <Text style={styles.bigPrimaryText}>Deschide garderoba</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.secondaryOutline} onPress={logout}>
            <Text style={styles.secondaryOutlineText}>Logout</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.dangerButton} onPress={handleDelete}>
            <Text style={styles.dangerText}>Șterge contul</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};
