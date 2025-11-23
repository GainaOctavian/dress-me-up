import { StyleSheet } from "react-native";
import { ThemeColors } from "../theme/colors";

export const createProfileStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    safeArea: {
      flex: 1,
      backgroundColor: colors.background,
    },
    center: {
      flex: 1,
      justifyContent: "center",
      alignItems: "center",
    },
    container: {
      flex: 1,
    },
    content: {
      padding: 20,
    },
    header: {
      marginBottom: 20,
    },
    title: {
      color: colors.heading,
      fontSize: 24,
      fontWeight: "700",
      marginBottom: 6,
      textAlign: "center",
    },
    subtitle: {
      color: colors.textMuted,
      fontSize: 14,
      textAlign: "center",
    },
    themeRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      padding: 16,
      borderRadius: 14,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
      marginBottom: 20,
    },
    themeTitle: {
      color: colors.text,
      fontWeight: "600",
      fontSize: 15,
    },
    themeSubtitle: {
      color: colors.textMuted,
      fontSize: 13,
      marginTop: 4,
    },
    error: {
      color: colors.accent,
      textAlign: "center",
      marginBottom: 12,
    },
    card: {
      backgroundColor: colors.card,
      borderRadius: 16,
      padding: 20,
      borderWidth: 1,
      borderColor: colors.border,
      marginBottom: 24,
    },
    cardHeader: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: 16,
    },
    cardTitle: {
      color: colors.text,
      fontSize: 18,
      fontWeight: "600",
    },
    editLink: {
      color: colors.primarySoft,
      fontWeight: "600",
      fontSize: 14,
    },
    row: {
      flexDirection: "row",
      justifyContent: "space-between",
      marginBottom: 10,
    },
    label: {
      color: colors.textMuted,
      fontSize: 14,
    },
    value: {
      color: colors.text,
      fontSize: 14,
      fontWeight: "500",
    },
    field: {
      marginBottom: 14,
    },
    fieldRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 14,
    },
    input: {
      marginTop: 6,
      backgroundColor: colors.inputBg,
      borderWidth: 1,
      borderColor: colors.inputBorder,
      borderRadius: 10,
      paddingHorizontal: 12,
      paddingVertical: 10,
      color: colors.text,
      fontSize: 15,
    },
    editActions: {
      flexDirection: "row",
      justifyContent: "flex-end",
      gap: 10,
      marginTop: 4,
    },
    primaryButton: {
      backgroundColor: colors.primary,
      paddingVertical: 10,
      paddingHorizontal: 18,
      borderRadius: 999,
    },
    primaryText: {
      color: colors.buttonTextOnPrimary,
      fontWeight: "600",
      fontSize: 14,
    },
    secondaryButton: {
      paddingVertical: 10,
      paddingHorizontal: 18,
      borderRadius: 999,
      borderWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.surface,
    },
    secondaryText: {
      color: colors.text,
      fontWeight: "500",
      fontSize: 14,
    },
    actions: {
      gap: 10,
      marginBottom: 24,
    },
    bigPrimaryButton: {
      backgroundColor: colors.primarySoft,
      paddingVertical: 14,
      borderRadius: 16,
    },
    bigPrimaryText: {
      color: colors.buttonTextOnPrimary,
      fontWeight: "600",
      fontSize: 16,
      textAlign: "center",
    },
    secondaryOutline: {
      borderWidth: 1,
      borderColor: colors.accent,
      borderRadius: 16,
      paddingVertical: 12,
    },
    secondaryOutlineText: {
      color: colors.accent,
      fontWeight: "600",
      fontSize: 15,
      textAlign: "center",
    },
    dangerButton: {
      marginTop: 8,
      paddingVertical: 10,
      borderRadius: 16,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.danger,
    },
    dangerText: {
      color: colors.danger,
      fontWeight: "600",
      fontSize: 14,
      textAlign: "center",
    },
  });
