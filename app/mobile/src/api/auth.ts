import { apiClient } from "./client";
import { LoginRequest, Token } from "../types/auth";

export async function login(request: LoginRequest): Promise<Token> {
  const form = new URLSearchParams();
  form.append("username", request.email);   // OAuth2PasswordRequestForm expects "username"
  form.append("password", request.password);

  return apiClient.postForm<Token>("/auth/token", form);
}
