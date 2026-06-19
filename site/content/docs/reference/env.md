---
title: "环境变量"
weight: 1
---

建议按以下维度整理：

- 前端构建与运行时变量
- 后端数据库与模型配置
- Compose 部署变量

第一版可以先以 `.env.example` 为基础逐步补充。

## 安全相关（可选）

以下两个后端变量默认关闭，保持向后兼容；按需开启可提升部署安全性。

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `API_AUTH_TOKEN` | 空（不启用） | 配置后，所有 `/api/v1` 接口需携带匹配令牌：`Authorization: Bearer <token>` 或 `X-API-Key: <token>`。`/health`、`/docs`、`/openapi.json`、`/redoc` 始终放行。启用后需让前端/调用方一并携带该令牌。 |
| `FIELD_ENCRYPTION_KEY` | 空（明文存储） | 配置后，供应商 `api_key` / `api_secret` 以静态加密形式落库（密文带 `enc::` 前缀）。历史明文可继续读取，并在下次写入时自动转为密文。一旦用于生产数据请勿更换密钥，否则历史密文无法解密。 |

