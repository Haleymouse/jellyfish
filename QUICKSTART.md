# Jellyfish 傻瓜式上手指南

照着复制粘贴就行。整个项目用 Docker 一条命令全套启动（前端、后端、数据库、缓存、存储都自动装好），不需要懂技术。

---

## 准备：装一个 Docker Desktop（只需一次）

去 <https://www.docker.com/products/docker-desktop/> 下载安装，打开它，等右下角小鲸鱼图标不再转圈（表示就绪）。**这是唯一需要装的软件。**

---

## 第 1 步：把代码下载到电脑

打开「终端」（Mac 用“终端”，Windows 用“PowerShell”），粘贴这两行回车：

```bash
git clone https://github.com/Haleymouse/jellyfish.git
cd jellyfish
```

> 如果提示没有 `git`：Mac 装 Xcode 命令行工具，或直接在 GitHub 仓库页点绿色 **Code → Download ZIP**，解压后进入那个文件夹。

---

## 第 2 步：一条命令启动全部

```bash
cp deploy/compose/.env.example deploy/compose/.env
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up --build
```

第一次会下载和构建，**耐心等几分钟**。看到日志里出现 `Uvicorn running` 之类字样，就说明起来了。**这个窗口别关**（关了就等于关掉程序）。

---

## 第 3 步：打开网页

浏览器访问 👉 **<http://localhost:7788>**

看到 Jellyfish 的界面，就成功了。✅

| 地址 | 用途 |
| --- | --- |
| <http://localhost:7788> | 前端操作界面 |
| <http://localhost:8000/docs> | 后端接口文档（可选） |

---

## 第 4 步：配一次模型（唯一必须手动的一步）

软件本身不带 AI，要接你自己的模型（需要一个 API Key，比如某个支持 OpenAI 格式的服务商）。

1. 在网页进入 **模型管理**（地址栏可直接输 `http://localhost:7788/models`）。
2. **新建供应商**：填名称、`Base URL`、`API Key`（从你的模型服务商那里拿）。
3. **新建模型**，建三类各一个：**文本 / 图片 / 视频**。
4. 把这三个分别**设为默认模型**。

> 没配这步的话，后面“拆分镜”“生成”会报错说没有默认模型 —— 这是最常见的卡点。

---

## 第 5 步：开始做你的第一个短剧

1. 进 **项目大厅**（`/projects`）→ 新建项目。
2. 进项目 → 新建**章节**。
3. 在章节里**粘贴剧本** → 点 AI **拆分镜**（自动拆成一个个镜头，抽取角色/场景/对白）。
4. 进**分镜编辑页**逐个**确认**抽取出来的信息，镜头会变成 `ready`。
5. 进**分镜工作室**，点**生成图片/视频**。
6. 在**任务中心**看进度，生成完就能看结果。

一句话流程：**配模型 → 建项目章节 → 粘剧本拆分镜 → 确认 → 生成 → 看任务**。

---

## 日常使用

- **关掉程序**：回到那个终端窗口按 `Ctrl + C`，或直接关 Docker Desktop。
- **下次再用**：进入 `jellyfish` 文件夹，跑一次（第二次不用 `--build`，更快）：

  ```bash
  docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up
  ```

  你的项目数据都还在。

---

## 出问题速查

| 现象 | 处理 |
| --- | --- |
| 网页打不开 | 等久一点；确认第 2 步终端窗口还开着、没报红色错误；确认 Docker Desktop 在运行 |
| 生成报“没有默认模型” | 回第 4 步，确认文本/图片/视频三类默认模型都设了 |
| 生成一直转 / 失败 | 多半是模型的 `Base URL` 或 `API Key` 填错，回模型管理改 |
| 端口被占用 | 改 `deploy/compose/.env` 里的端口，或关掉占用 7788/8000 的程序 |

---

> 更详细的逐步教程见 `site/content/docs/getting-started/first-drama.md`。
