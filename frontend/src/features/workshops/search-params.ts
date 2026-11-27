export const WORKSHOP_SEARCH_PAGE_SIZE = 12;
const FIRST_PAGE = 1;

export type RawSearchParams = Record<string, string | string[] | undefined>;

export type WorkshopSearchQuery = {
  city: string;
  search: string;
  page: number;
};

function firstValue(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value)?.trim() ?? "";
}

export function parseWorkshopSearchParams(params: RawSearchParams): WorkshopSearchQuery {
  const page = Number.parseInt(firstValue(params.page), 10);
  return {
    city: firstValue(params.city),
    search: firstValue(params.search),
    page: Number.isInteger(page) && page >= FIRST_PAGE ? page : FIRST_PAGE,
  };
}

export function buildWorkshopSearchQuery(
  query: WorkshopSearchQuery,
  page: number,
): Record<string, string> {
  return Object.fromEntries(
    Object.entries({ city: query.city, search: query.search, page: String(page) }).filter(
      ([key, value]) => value !== "" && !(key === "page" && value === String(FIRST_PAGE)),
    ),
  );
}
