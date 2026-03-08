import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
});

export const queryKeys = {
  healthLive: ["health", "live"] as const,
  healthReady: ["health", "ready"] as const,
  eventsList: (params: object) => ["events", "list", params] as const,
  eventDetail: (eventId: string) => ["events", "detail", eventId] as const,
  aggregateCount: (params: object) => ["aggregates", "count", params] as const,
  aggregateTopEventTypes: (params: object) => ["aggregates", "top-event-types", params] as const,
  aggregateTopUrls: (params: object) => ["aggregates", "top-urls", params] as const,
  aggregateUniqueUsers: (params: object) => ["aggregates", "unique-users", params] as const,
};

