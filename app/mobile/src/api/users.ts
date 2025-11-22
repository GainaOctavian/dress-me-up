import { apiClient } from "./client";
import {
  CreateUser,
  GetUser,
  GetAllUsers,
  UpdateUser,
} from "../types/user";

// POST /api/v1/users/
export async function createUser(payload: CreateUser): Promise<GetUser> {
  return apiClient.postJson<GetUser>("/users/", payload);
}

// GET /api/v1/users/me  (cu token)
export async function getCurrentUser(token: string): Promise<GetUser> {
  return apiClient.getWithAuth<GetUser>("/users/me", token);
}

// GET /api/v1/users/
export async function getUsers(): Promise<GetAllUsers> {
  return apiClient.get<GetAllUsers>("/users/");
}

// PUT /api/v1/users/me  (cu token)
export async function updateCurrentUser(
  token: string,
  payload: UpdateUser
): Promise<GetUser> {
  return apiClient.putJson<GetUser>("/users/me", payload);
}
