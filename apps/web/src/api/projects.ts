import { listProjectsApiProjectsGet } from "@my-agent/shared-types";

import type { PageResult, Project } from "./types";
import { requestData } from "@/utils/request";

export interface ListProjectsParams {
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

export async function listProjects(params: ListProjectsParams = {}): Promise<PageResult<Project>> {
  return requestData<PageResult<Project>>(
    listProjectsApiProjectsGet({
      query: params,
      throwOnError: true,
    }),
  );
}

export async function listAllProjects(): Promise<Project[]> {
  const page = await listProjects({ limit: 200, offset: 0 });
  return page.records;
}
