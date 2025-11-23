export type ThemeMode = "light" | "dark";

export type ThemeColors = {
  background: string;
  backgroundAlt: string;
  surface: string;
  card: string;
  border: string;

  text: string;
  textMuted: string;
  heading: string;

  primary: string;
  primarySoft: string;
  accent: string;
  danger: string;

  inputBg: string;
  inputBorder: string;

  buttonTextOnPrimary: string;
  buttonTextOnSurface: string;

  tabBarBg: string;
  tabBarBorder: string;
  tabActive: string;
  tabInactive: string;
};

export const darkColors: ThemeColors = {
  background: "#020617",
  backgroundAlt: "#0f172a",
  surface: "#020617",
  card: "#111827",
  border: "#1e293b",

  text: "#e5e7eb",
  textMuted: "#9ca3af",
  heading: "#f9fafb",

  primary: "#4f46e5",
  primarySoft: "#6366f1",
  accent: "#f97316",
  danger: "#ef4444",

  inputBg: "#020617",
  inputBorder: "#1e293b",

  buttonTextOnPrimary: "#f9fafb",
  buttonTextOnSurface: "#f97316",

  tabBarBg: "#020617",
  tabBarBorder: "#1e293b",
  tabActive: "#ffffff",
  tabInactive: "#64748b",
};

export const lightColors: ThemeColors = {
  background: "#f9fafb",
  backgroundAlt: "#e5e7eb",
  surface: "#ffffff",
  card: "#ffffff",
  border: "#e5e7eb",

  text: "#020617",
  textMuted: "#6b7280",
  heading: "#020617",

  primary: "#4f46e5",
  primarySoft: "#6366f1",
  accent: "#f97316",
  danger: "#ef4444",

  inputBg: "#f9fafb",
  inputBorder: "#d1d5db",

  buttonTextOnPrimary: "#f9fafb",
  buttonTextOnSurface: "#f97316",

  tabBarBg: "#ffffff",
  tabBarBorder: "#e5e7eb",
  tabActive: "#111827",
  tabInactive: "#9ca3af",
};
