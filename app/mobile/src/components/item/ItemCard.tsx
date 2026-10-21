import React, { useMemo } from "react";
import { TouchableOpacity, View, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Image } from "expo-image";

import { Item } from "../../types/item";
import { subcategoryLabel, useLayering } from "../../api/meta";
import { useTheme } from "../../hooks/useTheme";
import { createItemStyles } from "../../styles/item";

type Props = {
  item: Item;
  onPress?: () => void;
  // presigned URLs expire; the parent refetches when one fails
  onImageError?: () => void;
};

export const ItemCard: React.FC<Props> = ({ item, onPress, onImageError }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createItemStyles(colors), [colors]);
  const layering = useLayering();

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={0.8}
    >
      {item.image_url ? (
        <Image
          // cache by asset, not by URL: the signature changes on every fetch
          source={{ uri: item.image_url, cacheKey: item.image_asset_id ?? undefined }}
          style={styles.imagePlaceholder}
          // cutouts (processed) must not be cropped; raw photos fill the tile
          contentFit={item.image_status === "processed" ? "contain" : "cover"}
          transition={150}
          onError={onImageError}
          accessibilityLabel={item.name}
        />
      ) : (
        <View style={styles.imagePlaceholder}>
          <Ionicons name="shirt-outline" size={36} color={colors.textMuted} />
        </View>
      )}
      {(item.image_status === "ready" || item.image_status === "processing") && (
        <Text style={styles.meta}>Processing photo…</Text>
      )}
      <Text style={styles.name} numberOfLines={1}>
        {item.name}
      </Text>
      {(item.subcategory || item.categories.length > 0) && (
        <Text style={styles.meta} numberOfLines={1}>
          {item.subcategory
            ? subcategoryLabel(layering, item.subcategory)
            : item.categories.join(" · ")}
        </Text>
      )}
    </TouchableOpacity>
  );
};
