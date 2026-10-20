export interface User {
  id?: string;           // set by normalizeUser (api/users.ts)
  _id?: string;          // what the backend actually sends
  email: string;
  name?: string | null;
  private_profile: boolean;
  friend_ids: string[];
  [key: string]: any;    // extra fields (created_at etc.)
}

export interface GetUser {
  user: User;
}

export interface CreateUser {
  email: string;
  password: string;
  name?: string | null;
  private_profile?: boolean;
}

export interface UpdateUser {
  email?: string;
  password?: string;
  name?: string | null;
  private_profile?: boolean;
  friend_ids?: string[];
}
