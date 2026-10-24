import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import {
  answerFriendRequest,
  getFriendRequests,
  getFriends,
  removeFriend,
  sendFriendRequest,
} from "../../api/friends";
import { getCurrentUser } from "../../api/users";
import { errorMessage } from "../../api/client";
import { FriendRequests, PublicUser, displayName } from "../../types/friend";
import { confirmDestructive } from "../../utils/confirm";

// Plan 08: add by email, answer requests, list / remove friends.
export const FriendsScreen: React.FC = () => {
  const { token, setUser } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);

  const [friends, setFriends] = useState<PublicUser[] | null>(null);
  const [requests, setRequests] = useState<FriendRequests>({ incoming: [], outgoing: [] });
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const [f, r] = await Promise.all([getFriends(token), getFriendRequests(token)]);
      setFriends(f);
      setRequests(r);
    } catch (e) {
      setError(errorMessage(e, "Could not load your friends."));
    }
  }, [token]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  // runs a change, reloads, and refreshes the current user (Profile's count)
  const run = async (action: (t: string) => Promise<unknown>, fallback: string, done?: string) => {
    if (!token) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action(token);
      if (done) setNotice(done);
      await load();
      setUser((await getCurrentUser(token)).user);
    } catch (e) {
      setError(errorMessage(e, fallback));
    } finally {
      setBusy(false);
    }
  };

  const handleSend = () =>
    run(
      async (t) => {
        const r = await sendFriendRequest(t, email.trim());
        setEmail("");
        return r;
      },
      "Could not send the request.",
      "Request sent."
    );

  const handleRemove = async (friend: PublicUser) => {
    const ok = await confirmDestructive(
      "Remove friend",
      `Remove ${displayName(friend)} from your friends? You'll stop seeing each other's shared outfits.`,
      "Remove"
    );
    if (ok) void run((t) => removeFriend(t, friend._id), "Could not remove the friend.");
  };

  if (!friends) {
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

  return (
    <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text style={styles.title}>Friends</Text>
          <Text style={styles.subtitle}>Friends see the outfits you share.</Text>
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <View style={[styles.sectionCard, styles.form]}>
          <Text style={styles.metaLabel}>Add a friend by email</Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            style={styles.input}
            placeholder="friend@example.com"
            placeholderTextColor={colors.textMuted}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
          <TouchableOpacity
            onPress={handleSend}
            disabled={busy || !email.trim()}
            style={[styles.primaryButton, (busy || !email.trim()) && styles.buttonDisabled]}
          >
            <Text style={styles.primaryButtonText}>{busy ? "Saving…" : "Send request"}</Text>
          </TouchableOpacity>
          {notice ? <Text style={styles.memberSubtitle}>{notice}</Text> : null}
        </View>

        {requests.incoming.length > 0 && (
          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Requests</Text>
            {requests.incoming.map((r) => (
              <View key={r._id} style={[styles.memberRow, { marginTop: 10 }]}>
                <Text style={styles.memberName}>{displayName(r.user)}</Text>
                <View style={styles.chipRow}>
                  <TouchableOpacity
                    onPress={() => run((t) => answerFriendRequest(t, r._id, true), "Could not accept.")}
                    disabled={busy}
                    style={styles.chip}
                  >
                    <Text style={styles.chipText}>Accept</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    onPress={() => run((t) => answerFriendRequest(t, r._id, false), "Could not decline.")}
                    disabled={busy}
                    style={[styles.chip, styles.chipInactive]}
                  >
                    <Text style={[styles.chipText, styles.chipTextInactive]}>Decline</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </View>
        )}

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Your friends</Text>
          {friends.length === 0 ? (
            <Text style={[styles.memberSubtitle, { marginTop: 8 }]}>No friends yet.</Text>
          ) : (
            friends.map((f) => (
              <View key={f._id} style={[styles.memberRow, { marginTop: 10 }]}>
                <View>
                  <Text style={styles.memberName}>{displayName(f)}</Text>
                  {f.name && f.email ? <Text style={styles.memberSubtitle}>{f.email}</Text> : null}
                </View>
                <TouchableOpacity
                  onPress={() => handleRemove(f)}
                  disabled={busy}
                  style={[styles.chip, styles.chipInactive]}
                >
                  <Text style={[styles.chipText, { color: colors.danger }]}>Remove</Text>
                </TouchableOpacity>
              </View>
            ))
          )}
          {requests.outgoing.map((r) => (
            <View key={r._id} style={[styles.memberRow, { marginTop: 10 }]}>
              <Text style={styles.memberName}>{displayName(r.user)}</Text>
              <Text style={styles.memberSubtitle}>PENDING</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};
