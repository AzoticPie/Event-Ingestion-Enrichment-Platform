import type { ApiErrorModel } from "../lib/types";

export function LoadingState({ text = "Loading..." }: { text?: string }) {
  return <div className="state loading">{text}</div>;
}

export function EmptyState({ text }: { text: string }) {
  return <div className="state empty">{text}</div>;
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: ApiErrorModel | null;
  onRetry?: () => void;
}) {
  if (!error) {
    return null;
  }

  return (
    <div className="state error" role="alert">
      <p>
        <strong>
          {error.status} {error.code}
        </strong>
      </p>
      <p>{error.message}</p>
      {error.requestId && <p className="muted">request_id: {error.requestId}</p>}
      {onRetry && (
        <button type="button" className="secondary-button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

