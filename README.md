# ai-workflow-mcp-browser

在 Claude Code 中通过一条指令，驱动 Edge 浏览器依次访问多个 AI 网站，完成从需求到代码规格的全套规划流程。

---

## 工作原理

```
你写需求
   ↓
workflow_run
   ↓
Edge 浏览器自动打开（复用你已登录的账号）
   ↓
ChatGPT  → 生成技术方案      → STEP1_PLAN/draft_v1.md
DeepSeek → 审查方案问题      → STEP2_REVIEW/review_v1.md
ChatGPT  → 整合最终方案      → STEP3_ACCEPT/final_plan.md
Claude   → 生成实现规格文档   → STEP4_SPEC/spec.md
   ↓
workflow_execute
   ↓
Claude Code 读取规格，开始写代码
```

不需要任何 API Key。所有请求通过真实浏览器发出，复用你在 Edge Profile 2 里已经登录的账号。

---

## 安装

**第一步：下载文件**

把整个 `ai-workflow-mcp-browser` 文件夹放到你电脑上，例如：

```
C:\Users\你的用户名\ai-workflow-mcp-browser\
```

**第二步：双击运行 `setup.bat`**

它会自动完成：
- 安装 Python 依赖（playwright）
- 安装 Edge 浏览器驱动
- 把 MCP 插件注册到 Claude Code（所有项目都能用）

**第三步：验证**

打开 Claude Code，输入：

```
/mcp
```

看到 `ai-workflow-browser` 显示 5 个工具即安装成功。

---

## 使用流程

### 1. 准备需求文件

在你的项目目录下创建 `INPUT/demand.md`，写入你想开发的需求：

```markdown
开发一个 Python 工具，监控指定目录，自动把下载的文件按扩展名分类到子文件夹。

要求：
- 不使用第三方库
- 记录操作日志
- 处理文件重名冲突
- 支持 JSON 配置文件
```

### 2. 运行规划流程

在 Claude Code 中输入：

```
workflow_run
```

Edge 浏览器会自动打开，依次访问 ChatGPT、DeepSeek、ChatGPT、Claude.ai，全程可以看到浏览器操作过程。四个步骤全部完成大约需要 5～10 分钟。

### 3. 开始实现

```
workflow_execute
```

Claude Code 会收到完整的实现指令，然后在 `PROJECT/` 目录下创建项目、写代码、运行测试。

---

## 全部工具说明

| 工具 | 说明 |
|---|---|
| `workflow_run` | 运行完整的四步规划流程 |
| `workflow_execute` | 生成实现指令，让 Claude Code 开始写代码 |
| `workflow_status` | 查看哪些步骤已完成、文件大小 |
| `workflow_reset confirm=true` | 删除所有步骤文件，从头开始 |
| `git_commit message="..."` | 提交当前状态到 Git |

### 可选参数

**只跑部分步骤**（例如前面已跑过 plan，只想重新跑后三步）：

```
workflow_run steps=["review", "accept", "spec"]
```

**不显示浏览器窗口**（后台静默运行）：

```
workflow_run headless=true
```

**指定需求文件路径**：

```
workflow_run demand_path="C:\projects\myapp\requirements.md"
```

**指定代码输出目录**：

```
workflow_execute output_dir="C:\projects\myapp\src"
```

---

## 文件结构

```
ai-workflow-mcp-browser/
│
├── server.py              MCP 服务器主入口，处理所有工具调用
├── setup.bat              一键安装脚本
├── debug_selector.py      选择器调试工具（网站更新后用）
│
├── scrapers/
│   ├── base.py            公共工具：启动 Edge、输入文本、等待回复
│   ├── dispatcher.py      根据网站名路由到对应 scraper
│   ├── chatgpt.py         ChatGPT 操作脚本
│   ├── deepseek.py        DeepSeek 操作脚本
│   └── claude.py          Claude.ai 操作脚本
│
└── prompts/
    ├── planner.md         规划师提示词（发给 ChatGPT）
    ├── reviewer.md        审查专家提示词（发给 DeepSeek）
    ├── accept.md          技术负责人提示词（发给 ChatGPT）
    └── spec.md            规格文档提示词（发给 Claude.ai）
```

运行后，你的项目目录会生成：

```
你的项目/
├── INPUT/
│   └── demand.md          你写的需求
├── STEP1_PLAN/
│   └── draft_v1.md        ChatGPT 生成的技术方案
├── STEP2_REVIEW/
│   └── review_v1.md       DeepSeek 审查出的问题
├── STEP3_ACCEPT/
│   └── final_plan.md      整合后的最终方案
├── STEP4_SPEC/
│   └── spec.md            完整实现规格文档
└── PROJECT/               Claude Code 在这里写代码
```

---

## 修改使用哪个 AI 网站

编辑 `server.py` 顶部的 `STEP_SITES`：

```python
STEP_SITES = {
    "plan":   "chatgpt",   # 可改为 "deepseek" 或 "claude"
    "review": "deepseek",  # 可改为 "chatgpt" 或 "claude"
    "accept": "chatgpt",
    "spec":   "claude",
}
```

---

## 修改每步的提示词

直接编辑 `prompts/` 下对应的 `.md` 文件即可，无需改代码：

| 文件 | 对应步骤 | 作用 |
|---|---|---|
| `planner.md` | Step 1 | 告诉 AI 如何生成技术方案 |
| `reviewer.md` | Step 2 | 告诉 AI 审查哪些维度 |
| `accept.md` | Step 3 | 告诉 AI 如何整合方案 |
| `spec.md` | Step 4 | 告诉 AI 生成哪些规格文档 |

---

## 常见问题

**Q：运行时报错 "User data directory is already in use"**

Edge 浏览器和 Playwright 不能同时使用同一个 Profile。关闭所有 Edge 窗口再重试。或者在 Edge 中新建一个专用 Profile，在 `scrapers/base.py` 里把 `EDGE_PROFILE = "Profile 2"` 改成对应的文件夹名。

**Q：某个网站没有输入文字 / 没有抓到回复**

AI 网站前端经常更新，选择器可能失效。运行调试工具：

```bat
python debug_selector.py chatgpt
python debug_selector.py deepseek
python debug_selector.py claude
```

工具会打开浏览器并打印页面上所有输入框和消息容器的 class/id。对照结果，修改对应 scraper 文件里的 `INPUT_SEL` 和 `RESPONSE_SEL` 两个变量即可。

**Q：回复还没生成完就被截断了**

在对应 scraper 里调大 `stable_seconds`（判定完成前静止多少秒）或 `timeout`（最长等待秒数）：

```python
# 例如在 chatgpt.py 里
reply = wait_for_response_stable(page, RESPONSE_SEL, stable_seconds=5.0, timeout=300.0)
```

**Q：想换成 Chrome**

修改 `scrapers/base.py`：

```python
# channel 改为
channel="chrome",

# EDGE_USER_DATA 改为 Chrome 的路径
Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
```

---

## 卸载

```bat
claude mcp remove ai-workflow-browser
```
