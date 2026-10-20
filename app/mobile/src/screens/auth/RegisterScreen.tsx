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
      setError("Please fill in all required fields.");
      return false;
    }

    if (!trimmedEmail.includes("@")) {
      setError("Please enter a valid email.");
      return false;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return false;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
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
      setError("Sign up failed. Check your details and try again.");
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
