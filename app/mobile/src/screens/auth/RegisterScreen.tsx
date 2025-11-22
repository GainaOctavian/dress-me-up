import React, { useState } from "react";
import { createUser } from "../../api/users";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { AuthStackParamList } from "../../navigation/AuthNavigator";
import RegisterForm from "../../components/auth/RegisterForm";

type Props = NativeStackScreenProps<AuthStackParamList, "Register">;

export const RegisterScreen: React.FC<Props> = ({ navigation }) => {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const validate = () => {
    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password || !confirmPassword) {
      setError("Te rog completează toate câmpurile obligatorii.");
      return false;
    }

    if (!trimmedEmail.includes("@")) {
      setError("Te rog introdu un email valid.");
      return false;
    }

    if (password !== confirmPassword) {
      setError("Parolele nu coincid.");
      return false;
    }

    if (password.length < 6) {
      setError("Parola trebuie să aibă minim 6 caractere.");
      return false;
    }

    return true;
  };

  const handleRegister = async () => {
    setError("");

    if (!validate()) return;

    setLoading(true);

    try {
      await createUser({
        email: email.trim(),
        password,
        name: name.trim() || null,
        private_profile: true,
      });

      navigation.navigate("Login");
    } catch (err) {
      console.log("Register exception:", err);
      setError("Înregistrarea a eșuat. Verifică datele și încearcă din nou.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <RegisterForm
      email={email}
      name={name}
      password={password}
      confirmPassword={confirmPassword}
      loading={loading}
      error={error}
      onEmailChange={setEmail}
      onNameChange={setName}
      onPasswordChange={setPassword}
      onConfirmPasswordChange={setConfirmPassword}
      onSubmit={handleRegister}
      onSwitchToLogin={() => navigation.navigate("Login")}
    />
  );
};
