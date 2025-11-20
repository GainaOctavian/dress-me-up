import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";

type Props = {
  onSwitchToRegister: () => void;
};

export default function LoginScreen({ onSwitchToRegister }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Ecran Login (urmează să-l facem complet)</Text>

      <TouchableOpacity onPress={onSwitchToRegister}>
        <Text style={styles.link}>Nu ai cont? Înregistrează-te</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    justifyContent: "center",
    alignItems: "center",
  },
  text: {
    color: "white",
  },
  link: {
    color: "white",
    marginTop: 10,
  },
});
