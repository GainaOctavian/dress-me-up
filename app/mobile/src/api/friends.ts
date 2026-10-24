import { apiClient } from "./client";
import { Feed, FriendRequest, FriendRequests, PublicUser } from "../types/friend";

// Not cached: friends and the feed are always fetched fresh (plan 08).

export const getFriends = async (token: string): Promise<PublicUser[]> =>
  (await apiClient.getWithAuth<{ friends: PublicUser[] }>("/friends/", token)).friends;

export const getFriendRequests = (token: string) =>
  apiClient.getWithAuth<FriendRequests>("/friends/requests", token);

// by exact email; accepts their request if they already sent one
export const sendFriendRequest = async (token: string, email: string): Promise<FriendRequest> =>
  (await apiClient.postJsonWithAuth<{ request: FriendRequest }>("/friends/requests", token, { email }))
    .request;

export const answerFriendRequest = async (
  token: string,
  requestId: string,
  accept: boolean
): Promise<FriendRequest> =>
  (
    await apiClient.postJsonWithAuth<{ request: FriendRequest }>(
      `/friends/requests/${requestId}/${accept ? "accept" : "decline"}`,
      token
    )
  ).request;

export const removeFriend = (token: string, userId: string) =>
  apiClient.deleteWithAuth<void>(`/friends/${userId}`, token);

// friends' shared outfits, newest first; next page: before = last created_at
export const getFeed = (token: string, before?: string) =>
  apiClient.getWithAuth<Feed>(
    `/feed/${before ? `?before=${encodeURIComponent(before)}` : ""}`,
    token
  );
