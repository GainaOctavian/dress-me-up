import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  ScrollView,
} from "react-native";
import { useAuth } from "../../hooks/useAuth";
import { getCurrentUser } from "../../api/users";
import { User } from "../../types/user";

export const ProfileScreen: React.FC = () => {
  const { token, logout } = useAuth();

  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const loadUser = async () => {
    if (!token) return;

    setError("");
    setLoading(true);

    try {
      const response = await getCurrentUser(token);
      setUser(response.user);
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

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#fff"
        />
      }
    >
      <Text style={styles.title}>Bine ai venit în DressMeUp :3</Text>
      <Text style={styles.subtitle}>
        Asta e landing page-ul după login. De aici o să intri în wardrobe,
        prieteni, outfits generate etc.
      </Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {user && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Profil</Text>

          <View style={styles.row}>
            <Text style={styles.label}>Email</Text>
            <Text style={styles.value}>{user.email}</Text>
          </View>

          {user.name ? (
            <View style={styles.row}>
              <Text style={styles.label}>Nume</Text>
              <Text style={styles.value}>{user.name}</Text>
            </View>
          ) : null}

          <View style={styles.row}>
            <Text style={styles.label}>Profil privat</Text>
            <Text style={styles.value}>
              {user.private_profile ? "Da" : "Nu"}
            </Text>
          </View>

          <View style={styles.row}>
            <Text style={styles.label}>Prieteni</Text>
            <Text style={styles.value}>{user.friend_ids?.length ?? 0}</Text>
          </View>
        </View>
      )}

      <View style={styles.actions}>
        <TouchableOpacity style={styles.primaryButton}>
          <Text style={styles.primaryText}>Deschide garderoba</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton} onPress={logout}>
          <Text style={styles.secondaryText}>Logout</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  center: {
    flex: 1,
    backgroundColor: "#0f172a",
    justifyContent: "center",
    alignItems: "center",
  },
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
  content: {
    padding: 20,
  },
  title: {
    color: "#e5e7eb",
    fontSize: 24,
    fontWeight: "700",
    marginBottom: 8,
    textAlign: "center",
  },
  subtitle: {
    color: "#9ca3af",
    fontSize: 14,
    textAlign: "center",
    marginBottom: 24,
  },
  error: {
    color: "#f97316",
    textAlign: "center",
    marginBottom: 12,
  },
  card: {
    backgroundColor: "#111827",
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
  },
  cardTitle: {
    color: "#e5e7eb",
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 16,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  label: {
    color: "#9ca3af",
    fontSize: 14,
  },
  value: {
    color: "#e5e7eb",
    fontSize: 14,
    fontWeight: "500",
  },
  actions: {
    gap: 12,
  },
  primaryButton: {
    backgroundColor: "#4f46e5",
    paddingVertical: 12,
    borderRadius: 12,
  },
  primaryText: {
    color: "#f9fafb",
    textAlign: "center",
    fontWeight: "600",
    fontSize: 16,
  },
  secondaryButton: {
    borderWidth: 1,
    borderColor: "#f97316",
    paddingVertical: 10,
    borderRadius: 12,
  },
  secondaryText: {
    color: "#f97316",
    textAlign: "center",
    fontWeight: "600",
    fontSize: 15,
  },
});
