import React, { createContext, useState, ReactNode, useEffect } from "react";
import { login as loginApi } from "../api/auth";

type AuthContextType = {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: false,
  token: null,
  // funcții default doar ca să nu crape tipurile
  login: async () => {},
  logout: () => {},
});

type AuthProviderProps = {
  children: ReactNode;
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // aici ulterior poți încărca token-ul din AsyncStorage
  useEffect(() => {
    // TODO: load token from storage
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const tokenResponse = await loginApi({ email, password });
      setToken(tokenResponse.access_token);
      // TODO: salvează token în AsyncStorage
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    // TODO: șterge token din AsyncStorage
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!token,
        isLoading,
        token,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
