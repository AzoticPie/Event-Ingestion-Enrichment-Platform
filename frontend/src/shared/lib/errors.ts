import type { ApiErrorModel } from "./types";

export function asApiError(error: unknown): ApiErrorModel | null {
  if (!error) {
    return null;
  }

  if (isApiErrorModel(error)) {
    return error;
  }

  return {
    status: 0,
    code: "unknown_error",
    message: error instanceof Error ? error.message : "Unexpected error",
    requestId: null,
    detail: error,
  };
}

function isApiErrorModel(error: unknown): error is ApiErrorModel {
  if (typeof error !== "object" || error === null) {
    return false;
  }
  const candidate = error as Partial<ApiErrorModel>;
  return (
    typeof candidate.status === "number" &&
    typeof candidate.code === "string" &&
    typeof candidate.message === "string"
  );
}

