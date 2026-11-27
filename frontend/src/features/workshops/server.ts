import { notFound } from "next/navigation";

import {
  WORKSHOP_SEARCH_PAGE_SIZE,
  type WorkshopSearchQuery,
} from "@/features/workshops/search-params";
import { callApi } from "@/lib/api/call";
import { isApiErrorWithStatus } from "@/lib/api/errors";
import { serverApiClient } from "@/lib/api/server";
import type { WorkshopPublicDetail, WorkshopSummaryPage } from "@/lib/api/types";

const NOT_FOUND_STATUS = 404;

export function searchWorkshops(query: WorkshopSearchQuery): Promise<WorkshopSummaryPage> {
  return callApi(() =>
    serverApiClient.GET("/api/v1/workshops", {
      params: {
        query: {
          city: query.city || null,
          search: query.search || null,
          limit: WORKSHOP_SEARCH_PAGE_SIZE,
          offset: (query.page - 1) * WORKSHOP_SEARCH_PAGE_SIZE,
        },
      },
    }),
  );
}

export function listWorkshopCities(): Promise<string[]> {
  return callApi(() => serverApiClient.GET("/api/v1/workshops/cities"));
}

export async function getWorkshopBySlug(slug: string): Promise<WorkshopPublicDetail> {
  try {
    return await callApi(() =>
      serverApiClient.GET("/api/v1/workshops/slug/{slug}", { params: { path: { slug } } }),
    );
  } catch (error) {
    if (isApiErrorWithStatus(error, NOT_FOUND_STATUS)) {
      notFound();
    }
    throw error;
  }
}
