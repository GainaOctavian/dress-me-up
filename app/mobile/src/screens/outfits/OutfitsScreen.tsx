import React, { useMemo } from "react";
import { View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "../../hooks/useTheme";
import { createSimpleScreenStyles } from "../../styles/screen";

const OutfitsScreen: React.FC = () => {
  const { colors } = useTheme();
  const styles = useMemo(() => createSimpleScreenStyles(colors), [colors]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Text style={styles.title}>Outfits</Text>
        <Text style={styles.text}>
          Aici vei avea generarea de outfit-uri și lista cu cele salvate.
        </Text>
      </View>
    </SafeAreaView>
  );
};

export default OutfitsScreen;
