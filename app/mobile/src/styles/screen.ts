import { StyleSheet } from "react-native";
import { ThemeColors } from "../theme/colors";

export const createSimpleScreenStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    safeArea: {
      flex: 1,
      backgroundColor: colors.background,
    },
    container: {
      flex: 1,
      justifyContent: "center",
      alignItems: "center",
      padding: 20,
    },
    title: {
      color: colors.heading,
      fontSize: 22,
      fontWeight: "700",
      marginBottom: 8,
      textAlign: "center",
    },
    text: {
      color: colors.textMuted,
      textAlign: "center",
    },
  });
