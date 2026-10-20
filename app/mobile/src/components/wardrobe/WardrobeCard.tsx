import React, { useMemo } from "react";
import { TouchableOpacity, View, Text } from "react-native";
import { Wardrobe } from "../../types/wardrobe";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";

type Props = {
  wardrobe: Wardrobe;
  currentUserId?: string;
  onPress?: () => void;
};

export const WardrobeCard: React.FC<Props> = ({
  wardrobe,
  currentUserId,
  onPress,
}) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);

  const role = currentUserId ? wardrobe.roles[currentUserId] : undefined;

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={0.8}
    >
      <Text style={styles.cardTitle}>{wardrobe.name}</Text>

      {wardrobe.description ? (
        <Text style={styles.cardDescription}>{wardrobe.description}</Text>
      ) : null}

      <View style={styles.cardFooter}>
        <Text style={styles.createdAt}>
          Created: {new Date(wardrobe.created_at).toLocaleDateString()}
        </Text>

        {role && (
          <View style={styles.chip}>
            <Text style={styles.chipText}>{role.toUpperCase()}</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
};
