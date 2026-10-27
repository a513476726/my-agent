import { userMenuAdminMenuUserMenuAppGet } from "@my-agent/shared-types";

import type { Menu } from "./types";
import { requestData } from "@/utils/request";

export async function getUserMenus(app = "admin"): Promise<Menu[]> {
  return requestData<Menu[]>(
    userMenuAdminMenuUserMenuAppGet({
      path: { app },
      throwOnError: true,
    }),
  );
}
