import type { ApiErrorModel } from "../lib/types";

interface ApiErrorBannerProps {
  error: ApiErrorModel;
  onDismiss: () => void;
}

export function ApiErrorBanner({ error, onDismiss }: ApiErrorBannerProps) {
  return (
    <div className="api-error-banner" role="alert">
      <div>
        <strong>
          {error.status} {error.code}
        </strong>
        <p>{error.message}</p>
        {error.requestId && <p className="muted">request_id: {error.requestId}</p>}
      </div>
      <button type="button" className="ghost-button" onClick={onDismiss}>
        Dismiss
      </button>
    </div>
  );
}

