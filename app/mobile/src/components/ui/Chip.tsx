import React, { useMemo } from "react";
import { Text, TouchableOpacity } from "react-native";
import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";

type Props = {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  disabled?: boolean;
};

// Pill used for filters and pickers: filled when selected, outlined otherwise.
export const Chip: React.FC<Props> = ({
  label,
  selected = false,
  onPress,
  disabled,
}) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || !onPress}
      style={[styles.chip, !selected && styles.chipInactive]}
    >
      <Text style={[styles.chipText, !selected && styles.chipTextInactive]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
};
