/**
 * Vite 客户端类型声明
 * 
 * @description 为 Vite 提供 TypeScript 类型支持，包括环境变量和 .vue 文件类型
 * @see https://vitejs.dev/guide/features.html#typescript
 */
/// <reference types="vite/client" />

/**
 * .vue 文件类型声明
 * 
 * @description 让 TypeScript 能够正确识别 .vue 单文件组件
 */
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
