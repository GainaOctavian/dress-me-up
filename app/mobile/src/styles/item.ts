import { StyleSheet } from "react-native";
import { ThemeColors } from "../theme/colors";

export const createItemStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    grid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
      rowGap: 12,
    },
    card: {
      width: "48%",
      backgroundColor: colors.backgroundAlt,
      borderRadius: 12,
      padding: 8,
    },
    imagePlaceholder: {
      aspectRatio: 1,
      borderRadius: 8,
      backgroundColor: colors.card,
      alignItems: "center",
      justifyContent: "center",
    },
    name: {
      marginTop: 6,
      color: colors.text,
      fontSize: 14,
      fontWeight: "600",
    },
    meta: {
      color: colors.textMuted,
      fontSize: 12,
    },
    empty: {
      color: colors.textMuted,
      fontSize: 13,
    },
    hint: {
      color: colors.textMuted,
      fontSize: 12,
    },
    photo: {
      width: "100%",
      aspectRatio: 1,
      borderRadius: 12,
      backgroundColor: colors.card,
      alignItems: "center",
      justifyContent: "center",
      overflow: "hidden",
    },
    uploadOverlay: {
      position: "absolute", top: 0, right: 0, bottom: 0, left: 0,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: "rgba(0,0,0,0.35)", // dims the photo in both themes
    },
    chipWrap: {
      flexDirection: "row",
      flexWrap: "wrap",
      gap: 8,
    },
  });
