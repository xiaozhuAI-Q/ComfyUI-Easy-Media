# TODO.md

## 待处理

### 2025-05-18

- [x] 1.URL方式的转换，图片无法读取时从后端上传到input目录
- [ ] 2.NodeV2和日间模式下样式的适配，部分tailwind样式在NodeV2下需更正颜色定义
- [ ] 3.NodeV2下还需解决popover弹出后，点击节点内其他区域无法关闭popover的问题
- [x] 4.完善推送代码前的review
- [x] 5.补充本地化的初始配置
- [x] 6.补充音频轨道的简易裁切
- [ ] 7.补充 example_workflows（先完成 LTX2.3 PromptRelay的示例工作流编写）
- [ ] 8.完成 工作流 测试，提交预发布代码

## 初始化

### 后端 (Python)

- [x] `__init__.py` - 包初始化
  - [x] 导入 WEB 资源
  - [x] 导出 `__all__`
  - [x] 配置节点注册

- [x] `nodes.py` - 节点基础定义
  - [x] 基础节点结构编写

### 前端 (React)

- [x] `frontend/` - 前端目录结构
  - [x] `package.json` - Bun 项目配置
  - [x] `tsconfig.json` - TypeScript 配置
  - [x] `postcss.config.js` - PostCSS 配置
  - [x] `build.ts` - Bun 构建脚本、配置输出目录、chunk等
  - [x] `components.json` - shadcn/ui 组件配置
  - [x] `vitest.config.ts` - Vitest 测试配置
  - [x] `.eslintrc.json` - ESLint 配置

- [x] `frontend/src/` - 源代码目录
  - [x] `index.tsx` / `index.ts` - 入口文件（配置extensions）
  - [x] `src/lib/` - 工具函数
  - [x] `src/components/widgets` - 组件
  - [x] `src/components/ui/` - shadcn/ui 组件
  - [x] `src/types/` - TypeScript 类型定义

- [x] 依赖安装 (不要使用与vite相关的依赖库)
  - [x] 项目必要的依赖（如 React、Tailwind CSS、Vitest等）
  - [x] shadcn/ui 组件库、lucide 图标库等
  - [x] @comfyorg/comfyui-frontend-types 用于 comfyui-frontend 的类型支持

- [x] shadcn/ui 配置
  - [x] 基础组件 (Button, Input, Select 等)

### 构建

- [x] 构建验证
  - [x] 前端构建成功 (`bun run build.ts`)
