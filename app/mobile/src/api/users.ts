import { apiClient } from "./client";
import {
  CreateUser,
  GetUser,
  GetAllUsers,
  UpdateUser,
} from "../types/user";

// POST /users/
export async function createUser(payload: CreateUser): Promise<GetUser> {
  return apiClient.postJson<GetUser>("/users/", payload);
}

// GET /users/me
export async function getCurrentUser(token: string): Promise<GetUser> {
  return apiClient.getWithAuth<GetUser>("/users/me", token);
}

// GET /users/ (opțional)
export async function getUsers(): Promise<GetAllUsers> {
  return apiClient.get<GetAllUsers>("/users/");
}

// PUT /users/me
export async function updateCurrentUser(
  token: string,
  payload: UpdateUser
): Promise<GetUser> {
  return apiClient.putWithAuth<GetUser>("/users/me", token, payload);
}

// DELETE /users/me
export async function deleteCurrentUser(token: string): Promise<void> {
  return apiClient.deleteWithAuth<void>("/users/me", token);
}
