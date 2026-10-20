import { StyleSheet } from "react-native";
import { ThemeColors } from "../theme/colors";

export const createWardrobeStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    safeArea: {
      flex: 1,
      backgroundColor: colors.background,
    },
    container: {
      flex: 1,
      padding: 20,
    },
    header: {
      marginBottom: 16,
    },
    title: {
      color: colors.heading,
      fontSize: 22,
      fontWeight: "700",
      marginBottom: 4,
    },
    subtitle: {
      color: colors.textMuted,
      fontSize: 14,
    },
    // FlatList/ScrollView content: no flex:1, or the list can't scroll
    listContent: {
      padding: 20,
      paddingBottom: 32,
      rowGap: 12,
    },
    scrollContent: {
      padding: 20,
      paddingBottom: 32,
    },
    card: {
      backgroundColor: colors.card,
      borderRadius: 14,
      padding: 16,
      borderWidth: 1,
      borderColor: colors.border,
    },
    cardTitle: {
      color: colors.heading,
      fontSize: 16,
      fontWeight: "600",
    },
    cardDescription: {
      marginTop: 4,
      color: colors.textMuted,
      fontSize: 13,
    },
    cardFooter: {
      marginTop: 10,
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
    },
    createdAt: {
      color: colors.textMuted,
      fontSize: 12,
    },
    emptyContainer: {
      marginTop: 40,
      alignItems: "center",
    },
    emptyTitle: {
      color: colors.heading,
      fontSize: 18,
      fontWeight: "600",
      marginBottom: 6,
    },
    emptyText: {
      color: colors.textMuted,
      fontSize: 14,
      textAlign: "center",
    },
    errorText: {
      color: colors.accent,
      textAlign: "center",
      marginBottom: 8,
    },
    loaderContainer: {
      flex: 1,
      justifyContent: "center",
      alignItems: "center",
    },
    sectionCard: {
      backgroundColor: colors.card,
      borderRadius: 16,
      padding: 16,
      borderWidth: 1,
      borderColor: colors.border,
      marginBottom: 16,
    },
    sectionTitle: {
      color: colors.heading,
      fontSize: 16,
      fontWeight: "600",
      marginBottom: 8,
    },
    metaRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      marginTop: 4,
    },
    metaLabel: {
      color: colors.textMuted,
      fontSize: 13,
    },
    metaValue: {
      color: colors.text,
      fontSize: 14,
      fontWeight: "500",
    },
    chip: {
      paddingHorizontal: 10,
      paddingVertical: 4,
      borderRadius: 999,
      backgroundColor: colors.primarySoft,
      alignSelf: "flex-start",
    },
    chipInactive: {
      backgroundColor: "transparent",
      borderWidth: 1,
      borderColor: colors.border,
    },
    chipText: {
      color: colors.buttonTextOnPrimary,
      fontSize: 12,
      fontWeight: "600",
    },
    chipTextInactive: {
      color: colors.textMuted,
    },
    chipRow: {
      flexDirection: "row",
      gap: 8,
    },
    form: {
      gap: 8,
    },
    input: {
      borderWidth: 1,
      borderColor: colors.inputBorder,
      backgroundColor: colors.inputBg,
      borderRadius: 10,
      paddingHorizontal: 10,
      paddingVertical: 8,
      color: colors.text,
    },
    inputMultiline: {
      minHeight: 60,
      textAlignVertical: "top",
    },
    buttonRow: {
      flexDirection: "row",
      gap: 8,
      marginTop: 6,
    },
    primaryButton: {
      paddingVertical: 10,
      borderRadius: 999,
      alignItems: "center",
      backgroundColor: colors.primarySoft,
    },
    secondaryButton: {
      paddingVertical: 10,
      borderRadius: 999,
      alignItems: "center",
      borderWidth: 1,
      borderColor: colors.border,
    },
    buttonDisabled: {
      opacity: 0.5,
    },
    primaryButtonText: {
      color: colors.buttonTextOnPrimary,
      fontWeight: "600",
    },
    secondaryButtonText: {
      color: colors.text,
      fontWeight: "600",
    },
    memberRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      marginTop: 8,
    },
    memberName: {
      color: colors.text,
      fontSize: 14,
      fontWeight: "500",
    },
    memberSubtitle: {
      color: colors.textMuted,
      fontSize: 12,
    },
  });
