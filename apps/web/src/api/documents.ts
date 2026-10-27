import { listDocumentsApiDocumentsGet } from "@my-agent/shared-types";

import type { DocumentRecord, PageResult } from "./types";
import { requestData } from "@/utils/request";

export interface ListDocumentsParams {
  project_id: string;
  limit?: number;
  offset?: number;
}

export async function listDocuments(
  params: ListDocumentsParams,
): Promise<PageResult<DocumentRecord>> {
  return requestData<PageResult<DocumentRecord>>(
    listDocumentsApiDocumentsGet({
      query: params,
      throwOnError: true,
    }),
  );
}
