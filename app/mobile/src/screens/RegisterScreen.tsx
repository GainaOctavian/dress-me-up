import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from "react-native";

type RegisterScreenProps = {
  onRegistered: () => void;
  onSwitchToLogin: () => void;
};

export const RegisterScreen: React.FC<RegisterScreenProps> = ({
  onRegistered,
  onSwitchToLogin,
}) => {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API_BASE_URL = "http://192.168.0.101:8000"; // schimbă după IP-ul tău

  const handleRegister = async () => {
    setError("");

    if (!email || !password || !confirmPassword) {
      setError("Te rog completează toate câmpurile obligatorii.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Parolele nu coincid.");
      return;
    }

    if (password.length < 6) {
      setError("Parola trebuie să aibă minim 6 caractere.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/users`, {
        // !!! vezi mai jos explicația rutei !!!
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
          name: name || null,
          private_profile: true,
        }),
      });

      if (!response.ok) {
        const txt = await response.text();
        console.log("Register error:", txt);
        setError("Înregistrarea a eșuat. Verifică datele.");
        return;
      }

      Alert.alert("Succes!", "Cont creat. Loghează-te.", [
        { text: "OK", onPress: onRegistered },
      ]);
    } catch (err) {
      console.log(err);
      setError("Eroare de rețea. Verifică backend-ul.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.box}>
        <Text style={styles.title}>Creează un cont</Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TextInput
          placeholder="Email"
          keyboardType="email-address"
          style={styles.input}
          autoCapitalize="none"
          value={email}
          onChangeText={setEmail}
        />

        <TextInput
          placeholder="Nume (opțional)"
          style={styles.input}
          value={name}
          onChangeText={setName}
        />

        <TextInput
          placeholder="Parola"
          secureTextEntry
          style={styles.input}
          value={password}
          onChangeText={setPassword}
        />

        <TextInput
          placeholder="Confirmă parola"
          secureTextEntry
          style={styles.input}
          value={confirmPassword}
          onChangeText={setConfirmPassword}
        />

        <TouchableOpacity
          style={styles.button}
          onPress={handleRegister}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Înregistrează-te</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={onSwitchToLogin}>
          <Text style={styles.footerText}>
            Ai deja cont? <Text style={styles.link}>Conectează-te</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    justifyContent: "center",
    padding: 20,
  },
  box: {
    backgroundColor: "white",
    padding: 20,
    borderRadius: 16,
    elevation: 5,
  },
  title: {
    fontSize: 22,
    fontWeight: "600",
    marginBottom: 15,
    textAlign: "center",
  },
  input: {
    backgroundColor: "#f1f5f9",
    padding: 12,
    borderRadius: 10,
    marginBottom: 12,
    fontSize: 16,
  },
  button: {
    backgroundColor: "#0f172a",
    paddingVertical: 12,
    borderRadius: 10,
    marginTop: 10,
    marginBottom: 10,
  },
  buttonText: {
    color: "white",
    fontWeight: "600",
    textAlign: "center",
    fontSize: 16,
  },
  footerText: {
    textAlign: "center",
    marginTop: 8,
    color: "#334155",
  },
  link: {
    fontWeight: "600",
    color: "#0f172a",
  },
  error: {
    color: "red",
    marginBottom: 10,
    textAlign: "center",
  },
});
