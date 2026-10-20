import { Alert, Platform } from "react-native";

// Destructive-action confirmation that also works on web, where
// react-native-web's Alert.alert ignores buttons.
export function confirmDestructive(
  title: string,
  message: string,
  confirmText = "Delete"
): Promise<boolean> {
  if (Platform.OS === "web") {
    return Promise.resolve(window.confirm(`${title}\n\n${message}`));
  }
  return new Promise((resolve) =>
    Alert.alert(title, message, [
      { text: "Cancel", style: "cancel", onPress: () => resolve(false) },
      { text: confirmText, style: "destructive", onPress: () => resolve(true) },
    ])
  );
}
