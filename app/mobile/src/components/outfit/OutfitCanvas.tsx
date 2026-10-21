import React, { useMemo, useState } from "react";
import { LayoutChangeEvent, Text, View } from "react-native";
import { Image } from "expo-image";

import { Outfit, OutfitItem, OutfitItemRef } from "../../types/outfit";
import { useTheme } from "../../hooks/useTheme";
import { createOutfitStyles } from "../../styles/outfit";

type Props = {
  items: OutfitItem[];
  refs: Outfit["item_refs"];
  onImageError?: () => void;
};

// Read-only render of an outfit: square canvas, items placed by their
// normalized transforms (see models.Transform), drawn in z_index order.
// The editor (plan 06) reuses the same transform -> style mapping.
export const OutfitCanvas: React.FC<Props> = ({ items, refs, onImageError }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);
  const [size, setSize] = useState(0);

  const onLayout = (e: LayoutChangeEvent) => setSize(e.nativeEvent.layout.width);
  const drawn = items
    .filter((oi) => oi.visible && refs[oi.item_id])
    .sort((a, b) => a.z_index - b.z_index);

  return (
    <View style={styles.canvas} onLayout={onLayout}>
      {drawn.length === 0 && (
        <View style={styles.canvasEmpty}>
          <Text style={styles.noImageText}>No items</Text>
        </View>
      )}
      {size > 0 &&
        drawn.map((oi) => (
          <CanvasItem
            key={oi.item_id}
            item={oi}
            itemRef={refs[oi.item_id]}
            size={size}
            onImageError={onImageError}
          />
        ))}
    </View>
  );
};

const CanvasItem: React.FC<{
  item: OutfitItem;
  itemRef: OutfitItemRef;
  size: number;
  onImageError?: () => void;
}> = ({ item, itemRef, size, onImageError }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createOutfitStyles(colors), [colors]);
  const { translate, scale, rotation, flip_horizontal, flip_vertical } = item.transform;
  const w = size * 0.4 * scale.x;
  const h = size * 0.4 * scale.y;

  return (
    <View
      style={{
        position: "absolute",
        left: translate.x * size - w / 2,
        top: translate.y * size - h / 2,
        width: w,
        height: h,
        opacity: item.opacity,
        transform: [
          { rotate: `${rotation}deg` },
          { scaleX: flip_horizontal ? -1 : 1 },
          { scaleY: flip_vertical ? -1 : 1 },
        ],
      }}
    >
      {itemRef.image_url ? (
        <Image
          // cache per stored object (URL minus its changing signature)
          source={{ uri: itemRef.image_url, cacheKey: itemRef.image_url.split("?")[0] }}
          style={{ width: "100%", height: "100%" }}
          contentFit="contain"
          onError={onImageError}
          accessibilityLabel={itemRef.name}
        />
      ) : (
        <View style={styles.noImageBox}>
          <Text style={styles.noImageText} numberOfLines={2}>
            {itemRef.name}
          </Text>
        </View>
      )}
    </View>
  );
};
