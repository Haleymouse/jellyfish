---
title: "分镜工作室组件拆分计划"
weight: 20
description: "将 6000+ 行的 ChapterStudio 拆分为可维护的子组件与 hooks。"
---

## 背景

`front/src/pages/aiStudio/chapter/ChapterStudio.tsx` 体量已超过 6000 行，集中承载了
关键帧、参考图、视频参数、任务轮询、自动保存等全部逻辑，改动风险高、难以复用，
也与 `AGENTS.md` 中"重复样式/逻辑应抽离"的约定相悖。

任务轮询逻辑已先行抽离为 `services/taskPolling.ts`（指数退避，含单测），
本计划记录后续的渐进式拆分路径。

## 目标

- 单文件目标 < 500 行；
- 业务逻辑下沉到自定义 hooks，UI 拆分为聚焦的子组件；
- 每一步均以 `pnpm exec tsc --noEmit` 与 `pnpm run test` 兜底，避免回归。

## 拆分边界（建议按此分批，逐步提交）

1. **任务相关 hooks**
   - `useVideoTask`：视频生成提交 + 轮询 + 终态落地（复用 `pollTaskUntilDone`）。
   - `useFramePromptTask`、`useFrameImageTask`：提示词/分镜帧生成的提交与轮询。
   - 收口三处目前结构相似的轮询副作用。
2. **自动保存 hook**
   - `useDebouncedSave`：抽离 opsTitle/opsNote/videoPromptDraft 等多处 `setTimeout` 防抖保存。
3. **关键帧面板**
   - `KeyframePanel`：关键帧卡片状态、参考图选择、生成入口。
4. **视频参数面板**
   - `VideoParamsPanel`：比例/时长/种子/水印等参数与就绪度展示。
5. **任务状态展示**
   - 复用通用任务状态组件，避免在工作室内重复渲染逻辑。

## 风险控制

- 每批只移动一类职责，保持对外行为不变；
- 优先抽离"纯逻辑"（hooks），再抽离 UI 子组件；
- 为新 hooks 补 Vitest 用例（参考 `services/taskPolling.test.ts`）；
- 拆分过程中不改变接口契约，无需 `openapi:update`。

## 关联的可观测性改进（已落地）

- 后端新增 `/metrics`（Prometheus）暴露任务事件计数与时长直方图，
  便于在拆分/重构期间监控"生成卡住/失败率"是否回归。

## 仍待推进

- 任务状态由轮询切换为 SSE 推送（后端任务系统已内置 streaming 交付模式）。
- 生成任务的真正中途取消（当前为阶段间协作式取消 + 外部调用超时兜底）。
