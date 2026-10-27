<template>
  <template v-for="item in menuList" :key="getFullPath(item)">
    <!-- 没有子菜单的菜单项 -->
    <a-menu-item
      v-if="!item.children || item.children.length === 0"
      :key="getFullPath(item)"
      @click="handleItemClick(item)"
    >
      <!-- 只有一级菜单显示图标 -->
      <template #icon v-if="level === 0">
        <AppstoreOutlined />
      </template>
      <span>{{ item.label || item.meta?.title || item.name }}</span>
    </a-menu-item>

    <!-- 有子菜单的菜单项 -->
    <a-sub-menu v-else :key="getFullPath(item)">
      <!-- 只有一级菜单显示图标 -->
      <template #icon v-if="level === 0">
        <AppstoreOutlined />
      </template>
      <template #title>{{ item.label || item.meta?.title || item.name }}</template>
      <MenuItem
        :menu-list="item.children || []"
        :level="level + 1"
        :parent-path="getFullPath(item)"
      />
    </a-sub-menu>
  </template>
</template>

<script setup lang="ts">
import { AppstoreOutlined } from "@ant-design/icons-vue";

import type { Menu } from "@/api/types";
import { joinMenuPath } from "@/utils/route";

interface Props {
  menuList: Menu[]
  /**
   * 菜单层级，0 表示一级菜单
   * 一级菜单显示图标，二级及以后不显示图标
   */
  level?: number
  /**
   * 父菜单的完整路径（用于构建子菜单的完整路径）
   */
  parentPath?: string
}

const props = withDefaults(defineProps<Props>(), {
  level: 0,
  parentPath: "",
});

/**
 * 获取菜单项的完整路径
 * @param item 菜单项
 * @returns 完整路径
 */
const getFullPath = (item: Menu): string => {
  return joinMenuPath(props.parentPath, item.path || "");
};

// 点击事件由外层菜单根据 key 统一跳转，这里保留占位以便后续接入埋点。
const handleItemClick = (_item: Menu) => {
  void _item;
};
</script>
