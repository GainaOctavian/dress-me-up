import React, { useState } from "react";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { AuthStackParamList } from "../../navigation/AuthNavigator";
import { useAuth } from "../../hooks/useAuth";
import LoginForm from "../../components/auth/LoginForm";

type Props = NativeStackScreenProps<AuthStackParamList, "Login">;

export default function LoginScreen({ navigation }: Props) {
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const validate = () => {
    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password) {
      setError("Te rog completează emailul și parola.");
      return false;
    }

    if (!trimmedEmail.includes("@")) {
      setError("Te rog introdu un email valid.");
      return false;
    }

    return true;
  };

  const handleLogin = async () => {
    setError("");

    if (!validate()) return;

    setLoading(true);

    try {
      await login(email.trim(), password);
      // RootNavigation se ocupă de redirect spre AppNavigator
    } catch (err) {
      console.log("Login exception:", err);
      setError("Autentificarea a eșuat. Verifică datele și încearcă din nou.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <LoginForm
      email={email}
      password={password}
      loading={loading}
      error={error}
      onEmailChange={setEmail}
      onPasswordChange={setPassword}
      onSubmit={handleLogin}
      onSwitchToRegister={() => navigation.navigate("Register")}
    />
  );
}
