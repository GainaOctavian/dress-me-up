import React, { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Switch, Text, View } from "react-native";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { getBodies, getDefaultBodyId, setDefaultBodyId } from "../../api/bodies";
import { Body } from "../../types/body";
import { Chip } from "../ui/Chip";
import { BodyCanvas } from "./BodyCanvas";

// Profile card: pick the default mannequin for new outfits (plan 12).
export const MannequinSection: React.FC = () => {
  const { token } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  const [bodies, setBodies] = useState<Body[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [showKeypoints, setShowKeypoints] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = (forceRefresh = false) => {
    if (!token) return;
    getBodies(token, { forceRefresh })
      .then(setBodies)
      .catch(() => setError("Could not load mannequins."));
  };

  useEffect(() => {
    load();
    getDefaultBodyId().then(setSelected);
  }, [token]);

  const mannequins = (bodies ?? []).filter((b) => b.kind === "mannequin");
  const body = mannequins.find((b) => b.id === selected) ?? mannequins[0];
  const pose = body?.poses.neutral ?? (body ? Object.values(body.poses)[0] : undefined);

  return (
    <View style={styles.sectionCard}>
      <Text style={styles.sectionTitle}>Mannequin</Text>
      <Text style={[styles.metaLabel, { marginBottom: 8 }]}>
        New outfits start on this mannequin.
      </Text>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      {bodies === null && !error ? <ActivityIndicator color={colors.primarySoft} /> : null}

      <View style={[styles.chipRow, { marginBottom: 12 }]}>
        {mannequins.map((b) => (
          <Chip
            key={b.id}
            label={b.gender === "female" ? "Female" : "Male"}
            selected={body?.id === b.id}
            onPress={() => {
              setSelected(b.id);
              setDefaultBodyId(b.id);
            }}
          />
        ))}
      </View>

      {pose ? (
        <View style={{ width: "60%", alignSelf: "center" }}>
          <BodyCanvas pose={pose} showKeypoints={showKeypoints} onImageError={() => load(true)} />
        </View>
      ) : null}

      {__DEV__ && pose ? (
        <View style={[styles.metaRow, { marginTop: 12 }]}>
          <Text style={styles.metaLabel}>Show keypoints (dev)</Text>
          <Switch value={showKeypoints} onValueChange={setShowKeypoints} />
        </View>
      ) : null}
    </View>
  );
};
