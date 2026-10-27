import type {
  DocumentResponse,
  LoginResponse,
  MenuItem,
  MenuMeta,
  ProjectResponse,
  ReportResponse,
  UserInfoResponse,
} from "@my-agent/shared-types";

export type Project = ProjectResponse;
export type DocumentRecord = DocumentResponse;
export type ReportRecord = ReportResponse;
export type LoginResult = LoginResponse;
export type UserInfo = UserInfoResponse;
export type Menu = MenuItem;
export type { MenuMeta };

export interface PageResult<T> {
  records: T[];
  total: number;
}
