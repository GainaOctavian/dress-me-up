import { StyleSheet } from "react-native";
import { ThemeColors } from "../theme/colors";

export const createOutfitStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    canvas: {
      width: "100%",
      aspectRatio: 1,
      borderRadius: 12,
      backgroundColor: colors.backgroundAlt,
      overflow: "hidden",
    },
    selectedBox: {
      ...StyleSheet.absoluteFill,
      borderWidth: 1.5,
      borderColor: colors.primarySoft,
      borderStyle: "dashed",
      borderRadius: 4,
    },
    layerRow: {
      flexDirection: "row",
      alignItems: "center",
      paddingVertical: 6,
      paddingHorizontal: 8,
      borderRadius: 8,
      gap: 6,
    },
    layerRowSelected: {
      backgroundColor: colors.backgroundAlt,
    },
    layerName: {
      flex: 1,
      color: colors.text,
      fontSize: 14,
    },
    layerMeta: {
      color: colors.textMuted,
      fontSize: 12,
    },
    layerHidden: {
      opacity: 0.45,
    },
    iconButton: {
      padding: 4,
    },
    adjustRow: {
      flexDirection: "row",
      flexWrap: "wrap",
      alignItems: "center",
      gap: 6,
      marginTop: 8,
    },
    warningText: {
      color: colors.accent,
      fontSize: 13,
      marginBottom: 4,
    },
    renderBadge: {
      position: "absolute",
      bottom: 8,
      alignSelf: "center",
      paddingHorizontal: 10,
      paddingVertical: 4,
      borderRadius: 999,
      backgroundColor: colors.card,
      borderWidth: 1,
      borderColor: colors.border,
    },
    renderBadgeText: {
      color: colors.textMuted,
      fontSize: 12,
    },
    canvasEmpty: {
      ...StyleSheet.absoluteFill,
      alignItems: "center",
      justifyContent: "center",
    },
    noImageBox: {
      width: "100%",
      height: "100%",
      borderRadius: 8,
      borderWidth: 1,
      borderColor: colors.border,
      backgroundColor: colors.card,
      alignItems: "center",
      justifyContent: "center",
      padding: 4,
    },
    noImageText: {
      color: colors.textMuted,
      fontSize: 11,
      textAlign: "center",
    },
    card: {
      backgroundColor: colors.card,
      borderRadius: 14,
      padding: 10,
      borderWidth: 1,
      borderColor: colors.border,
    },
    cardTitle: {
      marginTop: 8,
      color: colors.heading,
      fontSize: 16,
      fontWeight: "600",
    },
    cardMeta: {
      color: colors.textMuted,
      fontSize: 12,
      marginTop: 2,
    },
    pickGrid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
      rowGap: 10,
    },
    pickCell: {
      width: "31%",
      borderRadius: 10,
      borderWidth: 2,
      borderColor: "transparent",
      padding: 4,
    },
    pickCellSelected: {
      borderColor: colors.primarySoft,
    },
    pickName: {
      color: colors.text,
      fontSize: 12,
      marginTop: 4,
    },
  });
