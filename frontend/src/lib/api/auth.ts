import { clearAccessToken, setAccessToken } from "@/lib/auth/token";
import type {
  AccessToken,
  Credentials,
  RegistrationDetails,
  User,
} from "@/types/auth";

import { apiClient } from "./client";

export type RegisterRequest = RegistrationDetails;
export type LoginRequest = Credentials;
export type TokenResponse = AccessToken;
export type UserResponse = User;

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
