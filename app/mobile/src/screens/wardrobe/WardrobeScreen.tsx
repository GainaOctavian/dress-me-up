import React, { useMemo } from "react";
import { View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "../../hooks/useTheme";
import { createSimpleScreenStyles } from "../../styles/screen";

const WardrobeScreen: React.FC = () => {
  const { colors } = useTheme();
  const styles = useMemo(() => createSimpleScreenStyles(colors), [colors]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Text style={styles.title}>Wardrobe</Text>
        <Text style={styles.text}>
          Aici o să apară lista cu haine, filtre și butonul de “Adaugă articol”.
        </Text>
      </View>
    </SafeAreaView>
  );
};

export default WardrobeScreen;
