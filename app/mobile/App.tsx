import React, { useState } from "react";
import { RegisterScreen } from "./src/screens/RegisterScreen";
import LoginScreen from "./src/screens/LoginScreen";

export default function App() {
  const [screen, setScreen] = useState<"register" | "login">("register");

  if (screen === "login") {
    return <LoginScreen onSwitchToRegister={() => setScreen("register")} />;
  }

  return (
    <RegisterScreen
      onRegistered={() => setScreen("login")}
      onSwitchToLogin={() => setScreen("login")}
    />
  );
}
