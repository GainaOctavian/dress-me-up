import { apiClient } from "./client";
import { cached, cacheKey } from "./cache";
import {
  CreateUser,
  GetUser,
  UpdateUser,
  User,
} from "../types/user";

// Backend serializează id-ul ca "_id"; în app folosim mereu user.id.
export const normalizeUser = (raw: User): User => ({
  ...raw,
  id: raw.id ?? raw._id,
});

// POST /users/
export async function createUser(payload: CreateUser): Promise<GetUser> {
  return apiClient.postJson<GetUser>("/users/", payload);
}

// GET /users/me
export async function getCurrentUser(token: string): Promise<GetUser> {
  const res = await apiClient.getWithAuth<GetUser>("/users/me", token);
  return { user: normalizeUser(res.user) };
}

// GET /users/{user_id} cu cache în AsyncStorage
export const getUserById = (
  token: string,
  userId: string,
  options?: { forceRefresh?: boolean }
): Promise<User> =>
  cached(
    cacheKey(`user:${userId}`),
    async () =>
      normalizeUser(
        (await apiClient.getWithAuth<GetUser>(`/users/${userId}`, token)).user
      ),
    options?.forceRefresh
  );

// PUT /users/me — AuthContext.setUser persistă userul curent
export async function updateCurrentUser(
  token: string,
  payload: UpdateUser
): Promise<GetUser> {
  const res = await apiClient.putWithAuth<GetUser>("/users/me", token, payload);
  return { user: normalizeUser(res.user) };
}

// DELETE /users/me
export async function deleteCurrentUser(token: string): Promise<void> {
  await apiClient.deleteWithAuth<void>("/users/me", token);
  // auth context va curăța storage-ul
}
