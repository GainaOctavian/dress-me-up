export const API_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "http://192.168.0.101:8080";

export const API_TIMEOUT = Number(
  process.env.EXPO_PUBLIC_API_TIMEOUT ?? 10000
);

export const API_BASE_URL = `${API_URL}/api/v1`;

export const APP_NAME = "DressMeUp";
