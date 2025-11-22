import React from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { authStyles as styles } from "../../styles/auth";

type LoginFormProps = {
  email: string;
  password: string;
  loading: boolean;
  error?: string;

  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;

  onSubmit: () => void;
  onSwitchToRegister: () => void;
};

const LoginForm: React.FC<LoginFormProps> = ({
                                               email,
                                               password,
                                               loading,
                                               error,
                                               onEmailChange,
                                               onPasswordChange,
                                               onSubmit,
                                               onSwitchToRegister,
                                             }) => {
  return (
    <View style={styles.container}>
      <View style={styles.box}>
        <Text style={styles.title}>Conectează-te</Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TextInput
          placeholder="Email"
          keyboardType="email-address"
          style={styles.input}
          autoCapitalize="none"
          autoCorrect={false}
          value={email}
          onChangeText={onEmailChange}
        />

        <TextInput
          placeholder="Parola"
          secureTextEntry
          style={styles.input}
          value={password}
          onChangeText={onPasswordChange}
        />

        <TouchableOpacity
          style={styles.button}
          onPress={onSubmit}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Autentifică-te</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={onSwitchToRegister}>
          <Text style={styles.footerText}>
            Nu ai cont? <Text style={styles.link}>Înregistrează-te</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

export default LoginForm;
