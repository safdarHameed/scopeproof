export interface User {
  id: string;
  email: string;
  full_name: string | null;
  company_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
  company_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}
