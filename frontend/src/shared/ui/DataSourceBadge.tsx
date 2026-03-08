import type { DataSource } from "../lib/types";

export function DataSourceBadge({ value }: { value: DataSource }) {
  return <span className={`data-source-badge ${value}`}>{value === "rollup" ? "Rollup" : "Direct Query"}</span>;
}

