import createClient from "openapi-fetch";

import type { paths } from "@/lib/api/schema";

const DEFAULT_BACKEND_URL = "http://localhost:8000";

export const serverApiClient = createClient<paths>({
  baseUrl: process.env.BACKEND_INTERNAL_URL ?? DEFAULT_BACKEND_URL,
});
