import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type User = Schemas["UserRead"];
export type UserRole = Schemas["UserRole"];
export type UserSortField = Schemas["UserSortField"];
export type SortOrder = Schemas["SortOrder"];
export type UserPage = Schemas["Page_UserRead_"];
export type AccessTokenResponse = Schemas["AccessTokenResponse"];
export type ErrorResponse = Schemas["ErrorResponse"];
export type BackendErrorCode = Schemas["ErrorCode"];

export const USER_ROLES = [
  "CLIENT",
  "MECHANIC",
  "MANAGER",
  "ADMIN",
] as const satisfies readonly UserRole[];
