import { loginAuthLoginPost, userInfoAdminUserInfoGet } from "@my-agent/shared-types";

import type { LoginResult, UserInfo } from "./types";
import { requestData } from "@/utils/request";

export async function login(username: string, password: string): Promise<LoginResult> {
  return requestData<LoginResult>(
    loginAuthLoginPost({
      body: { username, password },
      throwOnError: true,
    }),
  );
}

export async function getUserInfo(): Promise<UserInfo> {
  return requestData<UserInfo>(userInfoAdminUserInfoGet({ throwOnError: true }));
}
