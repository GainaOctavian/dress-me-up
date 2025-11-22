import React from "react";
import { AuthProvider } from "./src/context/AuthContext";
import { RootNavigation } from "./src/navigation";

export default function App() {
  return (
    <AuthProvider>
      <RootNavigation />
    </AuthProvider>
  );
}
