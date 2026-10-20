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
        <Text style={styles.title}>Create an account</Text>

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
          placeholder="Name (optional)"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          value={name}
          onChangeText={onNameChange}
        />

        <TextInput
          placeholder="Password"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
          style={styles.input}
          value={password}
          onChangeText={onPasswordChange}
        />

        <TextInput
          placeholder="Confirm password"
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
            <Text style={styles.buttonText}>Sign up</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={onSwitchToLogin}>
          <Text style={styles.footerText}>
            Already have an account? <Text style={styles.link}>Sign in</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

export default RegisterForm;
