import type { RouteLocationNormalized } from "vue-router";

import type { Menu } from "@/api/types";

function normalizePath(path: string): string {
  if (!path) return "/";
  return path.startsWith("/") ? path : `/${path}`;
}

export function joinMenuPath(parent: string, child: string): string {
  if (!child) return normalizePath(parent);
  if (child.startsWith("/")) return normalizePath(child);
  if (!parent) return normalizePath(child);
  return `${normalizePath(parent).replace(/\/$/, "")}/${child.replace(/^\/+/, "")}`;
}

export function resolveUrlPath(url: string): string {
  return normalizePath(url);
}

export function setUrlPath(route: RouteLocationNormalized): string {
  return route.path;
}

export function findMenuTrail(
  menus: Menu[],
  targetPath: string,
  parentPath = "",
): Menu[] {
  for (const menu of menus) {
    const fullPath = joinMenuPath(parentPath, menu.path);
    if (fullPath === normalizePath(targetPath)) {
      return [menu];
    }

    if (menu.children?.length) {
      const childTrail = findMenuTrail(menu.children, targetPath, fullPath);
      if (childTrail.length > 0) {
        return [menu, ...childTrail];
      }
    }
  }
  return [];
}

export function findMenuByPath(menus: Menu[], targetPath: string): Menu | undefined {
  return findMenuTrail(menus, targetPath).at(-1);
}

export interface MenuTrailItem {
  menu: Menu;
  fullPath: string;
  title: string;
}

export function getMenuTrailWithPaths(
  menus: Menu[],
  targetPath: string,
  parentPath = "",
): MenuTrailItem[] {
  for (const menu of menus) {
    const fullPath = joinMenuPath(parentPath, menu.path);
    const current: MenuTrailItem = { menu, fullPath, title: menuTitle(menu) };
    if (fullPath === normalizePath(targetPath)) {
      return [current];
    }

    if (menu.children?.length) {
      const childTrail = getMenuTrailWithPaths(menu.children, targetPath, fullPath);
      if (childTrail.length > 0) {
        return [current, ...childTrail];
      }
    }
  }
  return [];
}

export function getFirstLeafPath(menus: Menu[], parentPath = ""): string | undefined {
  for (const menu of menus) {
    const fullPath = joinMenuPath(parentPath, menu.path);
    if (menu.children?.length) {
      const childPath = getFirstLeafPath(menu.children, fullPath);
      if (childPath) return childPath;
    } else {
      return fullPath;
    }
  }
  return undefined;
}

export function flattenMenus(menus: Menu[], parentPath = ""): Array<{ menu: Menu; fullPath: string }> {
  return menus.flatMap((menu) => {
    const fullPath = joinMenuPath(parentPath, menu.path);
    return [
      { menu, fullPath },
      ...(menu.children?.length ? flattenMenus(menu.children, fullPath) : []),
    ];
  });
}

export function menuTitle(menu: Menu): string {
  return menu.label || menu.meta?.title || menu.name;
}
