import { listReportsApiReportsGet } from "@my-agent/shared-types";

import type { PageResult, ReportRecord } from "./types";
import { requestData } from "@/utils/request";

export interface ListReportsParams {
  project_id: string;
  kind?: "daily" | "weekly" | "quarterly";
  limit?: number;
  offset?: number;
}

export async function listReports(params: ListReportsParams): Promise<PageResult<ReportRecord>> {
  return requestData<PageResult<ReportRecord>>(
    listReportsApiReportsGet({
      query: params,
      throwOnError: true,
    }),
  );
}
