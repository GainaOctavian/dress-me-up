import { StyleSheet } from "react-native";
import { ThemeColors } from "../theme/colors";

export const createAuthStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
      justifyContent: "center",
      padding: 20,
    },
    box: {
      backgroundColor: colors.card,
      padding: 20,
      borderRadius: 16,
      elevation: 5,
      borderWidth: 1,
      borderColor: colors.border,
    },
    title: {
      fontSize: 22,
      fontWeight: "600",
      marginBottom: 15,
      textAlign: "center",
      color: colors.heading,
    },
    input: {
      backgroundColor: colors.inputBg,
      borderWidth: 1,
      borderColor: colors.inputBorder,
      padding: 12,
      borderRadius: 10,
      marginBottom: 12,
      fontSize: 16,
      color: colors.text,
    },
    button: {
      backgroundColor: colors.primary,
      paddingVertical: 12,
      borderRadius: 10,
      marginTop: 10,
      marginBottom: 10,
    },
    buttonText: {
      color: colors.buttonTextOnPrimary,
      fontWeight: "600",
      textAlign: "center",
      fontSize: 16,
    },
    footerText: {
      textAlign: "center",
      marginTop: 8,
      color: colors.textMuted,
    },
    link: {
      fontWeight: "600",
      color: colors.primarySoft,
    },
    error: {
      color: colors.accent,
      marginBottom: 10,
      textAlign: "center",
    },
  });
