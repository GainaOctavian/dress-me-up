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
