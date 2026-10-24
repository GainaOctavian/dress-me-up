import React, { useMemo } from "react";
import { Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useTheme } from "../../hooks/useTheme";
import { createWardrobeStyles } from "../../styles/wardrobe";
import { ModelViewer } from "../../components/outfit/ModelViewer";

// The outfit's dressed scene (renderer GLB), to turn round and zoom.
// Pushed from the outfit detail and the feed; same params in both stacks.
export type Outfit3DParams = { modelUrl: string; name: string };

export const Outfit3DScreen: React.FC<{ route: { params: Outfit3DParams } }> = ({ route }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createWardrobeStyles(colors), [colors]);
  return (
    <SafeAreaView style={styles.safeArea} edges={["bottom", "left", "right"]}>
      <View style={[styles.header, { paddingHorizontal: 16 }]}>
        <Text style={styles.title}>{route.params.name}</Text>
        <Text style={styles.subtitle}>Drag to turn the mannequin round, pinch to zoom.</Text>
      </View>
      <View style={{ flex: 1 }}>
        <ModelViewer url={route.params.modelUrl} background={colors.background} />
      </View>
    </SafeAreaView>
  );
};
