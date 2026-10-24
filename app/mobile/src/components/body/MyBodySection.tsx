import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Text, TextInput, TouchableOpacity, View } from "react-native";

import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { deleteMyBody, getBodies, myBody, saveMyBody } from "../../api/bodies";
import { errorMessage } from "../../api/client";
import { Body, MeasurementKey } from "../../types/body";
import { confirmDestructive } from "../../utils/confirm";
import { Chip } from "../ui/Chip";
import { BodyCanvas } from "./BodyCanvas";

const FIELDS: { key: MeasurementKey; label: string; required?: boolean }[] = [
  { key: "height_cm", label: "Height (cm)", required: true },
  { key: "weight_kg", label: "Weight (kg)", required: true },
  { key: "chest_cm", label: "Chest (cm)" },
  { key: "waist_cm", label: "Waist (cm)" },
  { key: "hips_cm", label: "Hips (cm)" },
];

// Profile card (plan 16a): my own body, built on the server from my
// measurements, then usable as "Me" wherever a mannequin is.
export const MyBodySection: React.FC<{ onChange?: () => void }> = ({ onChange }) => {
  const { token } = useAuth();
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  const [body, setBody] = useState<Body | null | undefined>(undefined); // undefined = loading
  const [editing, setEditing] = useState(false);
  const [gender, setGender] = useState<"male" | "female">("female");
  const [values, setValues] = useState<Partial<Record<MeasurementKey, string>>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (forceRefresh = false) => {
      if (!token) return;
      try {
        setBody(myBody(await getBodies(token, { forceRefresh })));
      } catch {
        setError("Could not load your body model.");
      }
    },
    [token]
  );
  useEffect(() => void load(true), [load]);

  // the server builds it in ~1.5 min: check back until it's done
  useEffect(() => {
    if (body?.status !== "building") return;
    const timer = setTimeout(() => {
      void load(true).then(onChange);
    }, 5000);
    return () => clearTimeout(timer);
  }, [body, load, onChange]);

  const startEdit = () => {
    setGender(body?.gender ?? "female");
    setValues(
      Object.fromEntries(
        Object.entries(body?.input_cm ?? {}).map(([k, v]) => [k, String(v)])
      ) as Partial<Record<MeasurementKey, string>>
    );
    setError(null);
    setEditing(true);
  };

  const num = (k: MeasurementKey) => {
    const v = parseFloat((values[k] ?? "").replace(",", "."));
    return Number.isFinite(v) ? v : undefined;
  };
  const canSave = !busy && num("height_cm") !== undefined && num("weight_kg") !== undefined;

  const handleSave = async () => {
    if (!token || !canSave) return;
    setBusy(true);
    setError(null);
    try {
      const extra = Object.fromEntries(
        FIELDS.filter((f) => !f.required && num(f.key) !== undefined).map((f) => [f.key, num(f.key)])
      );
      setBody(await saveMyBody(token, { gender, height_cm: num("height_cm")!, weight_kg: num("weight_kg")!, ...extra }));
      setEditing(false);
      onChange?.();
    } catch (e) {
      setError(errorMessage(e, "Could not save your measurements."));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!token) return;
    const ok = await confirmDestructive(
      "Delete my body",
      "Delete your body model now? Outfits dressed on it go back to a mannequin.",
      "Delete"
    );
    if (!ok) return;
    setBusy(true);
    try {
      await deleteMyBody(token);
      setBody(null);
      onChange?.();
    } catch (e) {
      setError(errorMessage(e, "Could not delete your body model."));
    } finally {
      setBusy(false);
    }
  };

  const pose = body?.poses.neutral;

  return (
    <View style={styles.sectionCard}>
      <Text style={styles.sectionTitle}>My body</Text>
      <Text style={[styles.metaLabel, { marginBottom: 8 }]}>
        A mannequin with your proportions, made from your measurements only. Private to you.
      </Text>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      {body === undefined && !error ? <ActivityIndicator color={colors.primarySoft} /> : null}

      {editing || body === null ? (
        <View style={styles.form}>
          <View style={styles.chipRow}>
            <Chip label="Female" selected={gender === "female"} onPress={() => setGender("female")} />
            <Chip label="Male" selected={gender === "male"} onPress={() => setGender("male")} />
          </View>
          {FIELDS.map((f) => (
            <View key={f.key}>
              <Text style={styles.metaLabel}>
                {f.label}
                {f.required ? "" : " · optional"}
              </Text>
              <TextInput
                value={values[f.key] ?? ""}
                onChangeText={(t) => setValues((v) => ({ ...v, [f.key]: t }))}
                style={styles.input}
                keyboardType="decimal-pad"
                placeholderTextColor={colors.textMuted}
                accessibilityLabel={f.label}
              />
            </View>
          ))}
          <Text style={styles.memberSubtitle}>
            Height and weight are enough; chest, waist and hips make the shape closer.
          </Text>
          <View style={styles.buttonRow}>
            <TouchableOpacity
              onPress={handleSave}
              disabled={!canSave}
              style={[styles.primaryButton, { flex: 1 }, !canSave && styles.buttonDisabled]}
            >
              <Text style={styles.primaryButtonText}>{busy ? "Saving…" : "Build my body"}</Text>
            </TouchableOpacity>
            {body ? (
              <TouchableOpacity onPress={() => setEditing(false)} style={[styles.secondaryButton, { flex: 1 }]}>
                <Text style={styles.secondaryButtonText}>Cancel</Text>
              </TouchableOpacity>
            ) : null}
          </View>
        </View>
      ) : body ? (
        <View>
          {body.status === "building" ? (
            <View style={[styles.metaRow, { marginBottom: 8 }]}>
              <ActivityIndicator color={colors.primarySoft} />
              <Text style={styles.memberSubtitle}>Building your body… about 2 minutes.</Text>
            </View>
          ) : null}
          {body.status === "failed" ? (
            <Text style={styles.errorText}>The build failed: {body.error ?? "unknown error"}. Try saving again.</Text>
          ) : null}
          {pose ? (
            <View style={{ width: "60%", alignSelf: "center" }}>
              <BodyCanvas pose={pose} onImageError={() => void load(true)} />
            </View>
          ) : null}
          {body.status === "ready" && Object.keys(body.measurements_cm).length ? (
            <Text style={[styles.memberSubtitle, { textAlign: "center", marginTop: 8 }]}>
              {["height", "chest", "waist", "hips"]
                .filter((k) => body.measurements_cm[k])
                .map((k) => `${k} ${Math.round(body.measurements_cm[k])} cm`)
                .join(" · ")}
            </Text>
          ) : null}
          <View style={[styles.buttonRow, { marginTop: 12 }]}>
            <TouchableOpacity onPress={startEdit} disabled={busy} style={[styles.secondaryButton, { flex: 1 }]}>
              <Text style={styles.secondaryButtonText}>Edit measurements</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={handleDelete} disabled={busy} style={[styles.secondaryButton, { flex: 1 }]}>
              <Text style={[styles.secondaryButtonText, { color: colors.danger }]}>Delete</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : null}
    </View>
  );
};
