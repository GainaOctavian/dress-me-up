export interface Token {
  access_token: string;
  token_type: string; // de obicei "Bearer"
}

export interface LoginRequest {
  email: string;    // va fi mapat pe "username" în form-data
  password: string;
}
