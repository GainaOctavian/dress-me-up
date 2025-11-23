import React, { useMemo } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { useTheme } from "../../hooks/useTheme";
import { createAuthStyles } from "../../styles/auth";

type RegisterFormProps = {
  email: string;
  name: string;
  password: string;
  confirmPassword: string;
  loading: boolean;
  error?: string;

  onEmailChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onConfirmPasswordChange: (value: string) => void;

  onSubmit: () => void;
  onSwitchToLogin: () => void;
};

const RegisterForm: React.FC<RegisterFormProps> = ({
                                                     email,
                                                     name,
                                                     password,
                                                     confirmPassword,
                                                     loading,
                                                     error,
                                                     onEmailChange,
                                                     onNameChange,
                                                     onPasswordChange,
                                                     onConfirmPasswordChange,
                                                     onSubmit,
                                                     onSwitchToLogin,
                                                   }) => {
  const { colors } = useTheme();
  const styles = useMemo(() => createAuthStyles(colors), [colors]);

  return (
    <View style={styles.container}>
      <View style={styles.box}>
        <Text style={styles.title}>Creează un cont</Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TextInput
          placeholder="Email"
          placeholderTextColor={colors.textMuted}
          keyboardType="email-address"
          style={styles.input}
          autoCapitalize="none"
          autoCorrect={false}
          value={email}
          onChangeText={onEmailChange}
        />

        <TextInput
          placeholder="Nume (opțional)"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={name}
          onChangeText={onNameChange}
        />

        <TextInput
          placeholder="Parola"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
          style={styles.input}
          value={password}
          onChangeText={onPasswordChange}
        />

        <TextInput
          placeholder="Confirmă parola"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
          style={styles.input}
          value={confirmPassword}
          onChangeText={onConfirmPasswordChange}
        />

        <TouchableOpacity
          style={styles.button}
          onPress={onSubmit}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color={colors.buttonTextOnPrimary} />
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

export default RegisterForm;
