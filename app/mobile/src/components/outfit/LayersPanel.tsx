import React, { useMemo } from "react";
import { Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { useTheme } from "../../hooks/useTheme";
import { createOutfitStyles } from "../../styles/outfit";
import { FitAdjust, OutfitItem, OutfitItemRef } from "../../types/outfit";
import { LayeringMeta } from "../../types/layering";
import { subcategoryLabel } from "../../api/meta";
import { drawOrder, NO_ADJUST, outfitWarnings, zOf } from "../../utils/fit";
import { Chip } from "../ui/Chip";

type Props = {
  items: OutfitItem[];
  refs: Record<string, OutfitItemRef>;
  meta: LayeringMeta;
  selectedId: string | null;
  onSelect: (itemId: string | null) => void;
  onChange: (items: OutfitItem[]) => void;
};

// Layers of a dressed outfit (plan 13), top layer first: visibility, tuck /
// into-shoes switches, reorder within a layer band, and fit tweaks for the
// selected item. Every change goes out as the full new item list.
export const LayersPanel: React.FC<Props> = ({ items, refs, meta, selectedId, onSelect, onChange }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);

  const order = drawOrder(items.filter((oi) => refs[oi.item_id]), refs, meta);
  const sub = (oi: OutfitItem) => refs[oi.item_id]?.subcategory ?? undefined;
  const info = (oi: OutfitItem) => {
    const s = sub(oi);
    return s ? meta.subcategories[s] : undefined;
  };
  const update = (id: string, patch: Partial<OutfitItem>) =>
    onChange(items.map((oi) => (oi.item_id === id ? { ...oi, ...patch } : oi)));

  // move past the neighbour in the same band (the rules decide across bands)
  const move = (index: number, dir: 1 | -1) => {
    const oi = order[index];
    const other = order[index + dir];
    if (!other || zOf(other, sub(other), meta) !== zOf(oi, sub(oi), meta)) return;
    update(oi.item_id, { layer_offset: (other.layer_offset ?? 0) + dir });
  };
  const canMove = (index: number, dir: 1 | -1) => {
    const other = order[index + dir];
    return !!other && zOf(other, sub(other), meta) === zOf(order[index], sub(order[index]), meta);
  };

  const selected = items.find((oi) => oi.item_id === selectedId);
  const adjust = (f: (a: FitAdjust) => FitAdjust) =>
    selected && update(selected.item_id, { fit_adjust: f(selected.fit_adjust ?? NO_ADJUST) });
  const warnings = outfitWarnings(items.map(sub), meta);

  return (
    <View>
      {warnings.map((w) => (
        <Text key={w} style={styles.warningText}>⚠ {w}</Text>
      ))}
      {order.map((oi, i) => ({ oi, i })).reverse().map(({ oi, i }) => {
        const s = info(oi);
        const tuckable = s?.slot === "torso" && ["mid", "insulation"].includes(s.role);
        const tucked = oi.tucked ?? s?.tucked_default ?? false;
        return (
          <View
            key={oi.item_id}
            style={[styles.layerRow, oi.item_id === selectedId && styles.layerRowSelected]}
          >
            <TouchableOpacity
              style={[{ flex: 1 }, !oi.visible && styles.layerHidden]}
              onPress={() => onSelect(oi.item_id === selectedId ? null : oi.item_id)}
              accessibilityLabel={`Select ${refs[oi.item_id].name}`}
            >
              <Text style={styles.layerName} numberOfLines={1}>{refs[oi.item_id].name}</Text>
              <Text style={styles.layerMeta}>{subcategoryLabel(meta, sub(oi)) || "No type"}</Text>
            </TouchableOpacity>
            {tuckable ? (
              <Chip
                label={tucked ? "Tucked" : "Untucked"}
                selected={tucked}
                onPress={() => update(oi.item_id, { tucked: !tucked })}
              />
            ) : null}
            {s?.slot === "legs" && s.role === "mid" ? (
              <Chip
                label="Into shoes"
                selected={!!oi.into_shoes}
                onPress={() => update(oi.item_id, { into_shoes: !oi.into_shoes })}
              />
            ) : null}
            <TouchableOpacity
              style={styles.iconButton}
              disabled={!canMove(i, 1)}
              onPress={() => move(i, 1)}
              accessibilityLabel={`Move ${refs[oi.item_id].name} up`}
            >
              <Ionicons name="chevron-up" size={18} color={canMove(i, 1) ? colors.text : colors.border} />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.iconButton}
              disabled={!canMove(i, -1)}
              onPress={() => move(i, -1)}
              accessibilityLabel={`Move ${refs[oi.item_id].name} down`}
            >
              <Ionicons name="chevron-down" size={18} color={canMove(i, -1) ? colors.text : colors.border} />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.iconButton}
              onPress={() => update(oi.item_id, { visible: !oi.visible })}
              accessibilityLabel={`${oi.visible ? "Hide" : "Show"} ${refs[oi.item_id].name}`}
            >
              <Ionicons name={oi.visible ? "eye-outline" : "eye-off-outline"} size={18} color={colors.text} />
            </TouchableOpacity>
          </View>
        );
      })}

      {selected ? (
        <View style={styles.adjustRow}>
          <Text style={styles.layerMeta}>Drag on the mannequin to move.</Text>
          <Chip label="Smaller" onPress={() => adjust((a) => ({ ...a, scale: Math.max(0.2, a.scale / 1.05) }))} />
          <Chip label="Bigger" onPress={() => adjust((a) => ({ ...a, scale: Math.min(5, a.scale * 1.05) }))} />
          <Chip label="↺" onPress={() => adjust((a) => ({ ...a, rotation: a.rotation - 5 }))} />
          <Chip label="↻" onPress={() => adjust((a) => ({ ...a, rotation: a.rotation + 5 }))} />
          <Chip label="Reset fit" onPress={() => update(selected.item_id, { fit_adjust: null })} />
        </View>
      ) : null}
    </View>
  );
};
