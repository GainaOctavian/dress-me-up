import React, { useMemo } from "react";
import { View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "../../hooks/useTheme";
import { createSimpleScreenStyles } from "../../styles/screen";

const SocialFeedScreen: React.FC = () => {
  const { colors } = useTheme();
  const styles = useMemo(() => createSimpleScreenStyles(colors), [colors]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Text style={styles.title}>Social Feed</Text>
        <Text style={styles.text}>
          Aici o să vezi postări de la prieteni și outfit-uri share-uite.
        </Text>
      </View>
    </SafeAreaView>
  );
};

export default SocialFeedScreen;
