import { healthHealthGet, type HealthData } from "@my-agent/shared-types";

import { requestData } from "@/utils/request";

export async function getHealth(): Promise<HealthData> {
  return requestData<HealthData>(healthHealthGet({ throwOnError: true }));
}
