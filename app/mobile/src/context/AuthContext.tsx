import React, {
  createContext,
  useState,
  ReactNode,
  useEffect,
} from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

import { login as loginApi } from "../api/auth";
import { getCurrentUser } from "../api/users";
import { clearCache, purgeOldCache } from "../api/cache";
import { setUnauthorizedHandler } from "../api/client";
import { User } from "../types/user";

const TOKEN_KEY = "auth:token";
const USER_KEY = "auth:user";

type AuthContextType = {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
};

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: true,
  token: null,
  user: null,
  login: async () => {},
  logout: () => {},
  setUser: () => {},
});

type AuthProviderProps = {
  children: ReactNode;
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUserState] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Hydrate from AsyncStorage on app start
  useEffect(() => {
    const hydrate = async () => {
      try {
        const [storedToken, storedUser] = await Promise.all([
          AsyncStorage.getItem(TOKEN_KEY),
          AsyncStorage.getItem(USER_KEY),
        ]);

        if (storedToken) {
          setToken(storedToken);
        }

        if (storedUser) {
          try {
            setUserState(JSON.parse(storedUser) as User);
          } catch (e) {
            console.log("Failed to parse stored user", e);
          }
        }
      } catch (e) {
        console.log("Failed to hydrate auth from storage", e);
      } finally {
        setIsLoading(false);
      }
    };

    void hydrate();
    void purgeOldCache().catch(() => {});
  }, []);

  const setUser = (next: User) => {
    setUserState(next);
    void AsyncStorage.setItem(USER_KEY, JSON.stringify(next));
  };

  // isLoading is only for the initial hydrate: toggling it here would make
  // RootNavigation unmount LoginScreen (and its error message) mid-login.
  // LoginScreen tracks its own loading state.
  const login = async (email: string, password: string) => {
    const { access_token } = await loginApi({ email, password });
    // fetch the user before committing the token, so a failure here
    // doesn't leave us "authenticated" without a user
    const { user: currentUser } = await getCurrentUser(access_token);

    await AsyncStorage.multiSet([
      [TOKEN_KEY, access_token],
      [USER_KEY, JSON.stringify(currentUser)],
    ]);
    setUserState(currentUser);
    setToken(access_token);
  };

  const logout = () => {
    setToken(null);
    setUserState(null);
    // also drop cached wardrobes/users, so the next account on this device
    // doesn't see the previous one's data
    void AsyncStorage.multiRemove([TOKEN_KEY, USER_KEY]);
    void clearCache();
  };

  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!token,
        isLoading,
        token,
        user,
        login,
        logout,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
