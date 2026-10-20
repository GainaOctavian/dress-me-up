import React, { useMemo } from "react";
import { TouchableOpacity, View, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { Item } from "../../types/item";
import { useTheme } from "../../hooks/useTheme";
import { createItemStyles } from "../../styles/item";

type Props = {
  item: Item;
  onPress?: () => void;
};

export const ItemCard: React.FC<Props> = ({ item, onPress }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createItemStyles(colors), [colors]);

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={0.8}
    >
      {/* real image comes with plan 03 (image upload) */}
      <View style={styles.imagePlaceholder}>
        <Ionicons name="shirt-outline" size={36} color={colors.textMuted} />
      </View>
      <Text style={styles.name} numberOfLines={1}>
        {item.name}
      </Text>
      {item.categories.length > 0 && (
        <Text style={styles.meta} numberOfLines={1}>
          {item.categories.join(" · ")}
        </Text>
      )}
    </TouchableOpacity>
  );
};
