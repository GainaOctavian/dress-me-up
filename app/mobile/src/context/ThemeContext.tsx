import React, { createContext, useState, useMemo, ReactNode } from "react";
import { useColorScheme } from "react-native";
import { ThemeMode, ThemeColors, darkColors, lightColors } from "../theme/colors";

type ThemeContextType = {
  mode: ThemeMode;
  colors: ThemeColors;
  toggleTheme: () => void;
  setMode: (mode: ThemeMode) => void;
};

export const ThemeContext = createContext<ThemeContextType>({
  mode: "dark",
  colors: darkColors,
  toggleTheme: () => {},
  setMode: () => {},
});

type Props = {
  children: ReactNode;
};

export const ThemeProvider: React.FC<Props> = ({ children }) => {
  const systemScheme = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>(
    systemScheme === "light" ? "light" : "dark"
  );

  const setMode = (m: ThemeMode) => setModeState(m);

  const toggleTheme = () => {
    setModeState((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const colors = useMemo<ThemeColors>(
    () => (mode === "dark" ? darkColors : lightColors),
    [mode]
  );

  const value: ThemeContextType = {
    mode,
    colors,
    toggleTheme,
    setMode,
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};
