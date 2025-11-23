export interface Token {
  access_token: string;
  token_type: string; // "Bearer"
}

export interface LoginRequest {
  email: string;
  password: string;
}
