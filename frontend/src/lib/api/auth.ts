import { clearAccessToken, setAccessToken } from "../auth-token";
import { apiClient } from "./client";
import type { ISODateString, UUID } from "./types";

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: UUID;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export async function registerUser(data: RegisterRequest): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>("/api/v1/auth/register", data);
  return response.data;
}

export async function loginUser(data: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/api/v1/auth/login", data);
  setAccessToken(response.data.access_token);
  return response.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>("/api/v1/auth/me");
  return response.data;
}

export function logoutUser(): void {
  clearAccessToken();
}

export const authApi = {
  register: registerUser,
  login: loginUser,
  me: getCurrentUser,
  logout: logoutUser,
};
