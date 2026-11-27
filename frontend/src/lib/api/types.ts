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

export type WorkshopSummary = Schemas["WorkshopSummary"];
export type WorkshopRead = Schemas["WorkshopRead"];
export type WorkshopPage = Schemas["Page_WorkshopRead_"];
export type WorkshopSummaryPage = Schemas["Page_WorkshopSummary_"];
export type WorkshopPublicDetail = Schemas["WorkshopPublicDetail"];
export type WorkshopStaffDetail = Schemas["WorkshopStaffDetail"];
export type WorkshopMember = Schemas["WorkshopMemberRead"];
export type OpeningHoursEntry = Schemas["OpeningHoursEntry"];
export type Closure = Schemas["ClosureRead"];
export type Bay = Schemas["BayRead"];
export type BayType = Schemas["BayType"];
export type ServiceType = Schemas["ServiceTypeRead"];
export type Vehicle = Schemas["VehicleRead"];
export type VehiclePage = Schemas["Page_VehicleRead_"];

export const USER_ROLES = [
  "CLIENT",
  "MECHANIC",
  "MANAGER",
  "ADMIN",
] as const satisfies readonly UserRole[];

export const STAFF_ROLES = ["MANAGER", "MECHANIC"] as const satisfies readonly UserRole[];
export const ADMIN_ROLES = ["ADMIN"] as const satisfies readonly UserRole[];

export const BAY_TYPES = [
  "GENERAL",
  "LIFT",
  "DIAGNOSTIC",
  "TIRES",
] as const satisfies readonly BayType[];

export const VAT_RATES = ["23", "8", "5", "0"] as const;
