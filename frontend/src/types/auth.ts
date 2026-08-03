import type { ISODateString, UUID } from "./api";

export interface User {
  id: UUID;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface Credentials {
  email: string;
  password: string;
}

export interface RegistrationDetails extends Credentials {
  full_name?: string | null;
}

export interface AccessToken {
  access_token: string;
  token_type: string;
}
