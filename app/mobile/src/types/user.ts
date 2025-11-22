export interface User {
  id?: string;           // dacă backend-ul folosește "id"
  _id?: string;          // dacă la tine în Mongo e _id
  email: string;
  name?: string | null;
  private_profile: boolean;
  friend_ids: string[];
  [key: string]: any;    // extra fields (created_at etc.)
}

export interface GetUser {
  user: User;
}

export interface GetAllUsers {
  users: User[];
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
