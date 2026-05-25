#!/usr/bin/env python3
"""
ai-workflow-mcp-browser
=======================
通过 Playwright 驱动 Edge 浏览器，复用已登录的 cookie，
依次调用各 AI 网站完成多步规划工作流。

暴露的 MCP 工具：
  workflow_run      — 完整跑 plan→review→accept→spec 四步
  workflow_execute  — 返回给 Claude Code 的实现指令
  workflow_status   — 查看各步骤文件
  workflow_reset    — 清空步骤文件
  git_commit        — 提交当前状态
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# ── MCP wire protocol (stdio JSON-RPC 2.0) ───────────────────────────────────

def send(obj: dict):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def respond(req_id, result):
    send({"jsonrpc": "2.0", "id": req_id, "result": result})

def error_response(req_id, code: int, message: str):
    send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})

# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "workflow_run",
        "description": (
            "用浏览器自动化依次调用 AI 网站，完成 plan→review→accept→spec 四步规划流程。"
            "每步输出保存到 ai-team/ 目录。默认读取项目根目录下的 INPUT/demand.md。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "demand_path": {
                    "type": "string",
                    "description": "需求文件路径，默认为项目根目录下的 INPUT/demand.md"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["plan", "review", "accept", "spec"]
                    },
                    "description": "要执行的步骤，默认全部执行"
                },
                "headless": {
                    "type": "boolean",
                    "description": "是否无头模式运行浏览器，默认 false（可以看到浏览器操作过程）"
                }
            }
        }
    },
    {
        "name": "workflow_execute",
        "description": "读取 STEP4_SPEC/spec.md，返回供 Claude Code 直接使用的实现指令。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "output_dir": {
                    "type": "string",
                    "description": "代码输出目录，默认为项目根目录下的 PROJECT/"
                }
            }
        }
    },
    {
        "name": "workflow_status",
        "description": "显示各步骤输出文件是否存在及大小。",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "workflow_reset",
        "description": "删除所有步骤文件，从头重来。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "confirm": {"type": "boolean", "description": "必须传 true 才会执行"}
            },
            "required": ["confirm"]
        }
    },
    {
        "name": "git_commit",
        "description": "在项目根目录执行 git add . && git commit。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "提交信息"}
            },
            "required": ["message"]
        }
    }
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR", "")
    return Path(raw) if raw else Path.cwd()

def read_prompt(name: str) -> str:
    p = Path(__file__).parent / "prompts" / f"{name}.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""

def ensure_dirs(root: Path):
    for d in ["INPUT", "STEP1_PLAN", "STEP2_REVIEW", "STEP3_ACCEPT", "STEP4_SPEC", "PROJECT"]:
        (root / d).mkdir(parents=True, exist_ok=True)

# ── Step 路由表：每步用哪个网站 ───────────────────────────────────────────────
#   可以自由修改，换成任意网站组合

STEP_SITES = {
    "plan":   "chatgpt",     # ChatGPT → 生成技术方案
    "review": "deepseek",    # DeepSeek → 审查
    "accept": "chatgpt",     # ChatGPT → 验收整合
    "spec":   "claude",      # Claude.ai → 生成 Spec
}

# ── Tool handlers ─────────────────────────────────────────────────────────────

def handle_workflow_run(args: dict) -> str:
    root = project_root()
    ensure_dirs(root)
    headless = args.get("headless", False)

    demand_path = args.get("demand_path")
    demand_file = Path(demand_path) if demand_path else root / "INPUT" / "demand.md"

    if not demand_file.exists():
        return (
            f"❌ 未找到需求文件：{demand_file}\n\n"
            f"请先创建它：\n"
            f"  mkdir INPUT\n"
            f"  在 INPUT/demand.md 中写入你的需求"
        )

    demand = demand_file.read_text(encoding="utf-8")
    steps = args.get("steps") or ["plan", "review", "accept", "spec"]
    log = []

    plan_text = review_text = accept_text = ""

    def try_read(path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    plan_file   = root / "STEP1_PLAN"   / "draft_v1.md"
    review_file = root / "STEP2_REVIEW" / "review_v1.md"
    accept_file = root / "STEP3_ACCEPT" / "final_plan.md"
    spec_file   = root / "STEP4_SPEC"   / "spec.md"

    # ── 整个流程共用一个浏览器实例，避免反复开关 ─────────────────────────────
    from scrapers.base import launch_edge
    from scrapers.dispatcher import ask

    pw, ctx = launch_edge(headless=headless)
    page = ctx.new_page()

    try:
        # ── PLAN ─────────────────────────────────────────────────────────────
        if "plan" in steps:
            log.append(f"⏳ Step 1：规划中（{STEP_SITES['plan']}）...")
            full_prompt = f"{read_prompt('planner')}\n\n# 需求\n\n{demand}"
            plan_text = ask(page=page, site=STEP_SITES["plan"], prompt=full_prompt)
            plan_file.write_text(plan_text, encoding="utf-8")
            log.append(f"✅ 规划完成 → {plan_file.relative_to(root)}")
        else:
            plan_text = try_read(plan_file)

        # ── REVIEW ───────────────────────────────────────────────────────────
        if "review" in steps:
            if not plan_text:
                return "❌ 没有规划结果，请先执行 plan 步骤"
            log.append(f"⏳ Step 2：审查中（{STEP_SITES['review']}）...")
            full_prompt = f"{read_prompt('reviewer')}\n\n# 待审查的方案\n\n{plan_text}"
            review_text = ask(page=page, site=STEP_SITES["review"], prompt=full_prompt)
            review_file.write_text(review_text, encoding="utf-8")
            log.append(f"✅ 审查完成 → {review_file.relative_to(root)}")
        else:
            review_text = try_read(review_file)

        # ── ACCEPT ───────────────────────────────────────────────────────────
        if "accept" in steps:
            if not plan_text or not review_text:
                return "❌ 缺少规划或审查结果，请先执行前面的步骤"
            log.append(f"⏳ Step 3：验收整合中（{STEP_SITES['accept']}）...")
            full_prompt = (
                f"{read_prompt('accept')}\n\n"
                f"# 初稿方案\n\n{plan_text}\n\n"
                f"# 审查意见\n\n{review_text}"
            )
            accept_text = ask(page=page, site=STEP_SITES["accept"], prompt=full_prompt)
            accept_file.write_text(accept_text, encoding="utf-8")
            log.append(f"✅ 验收完成 → {accept_file.relative_to(root)}")
        else:
            accept_text = try_read(accept_file)

        # ── SPEC ─────────────────────────────────────────────────────────────
        if "spec" in steps:
            if not accept_text:
                return "❌ 缺少验收结果，请先执行前面的步骤"
            log.append(f"⏳ Step 4：生成 Spec 中（{STEP_SITES['spec']}）...")
            full_prompt = f"{read_prompt('spec')}\n\n# 最终方案\n\n{accept_text}"
            spec_text = ask(page=page, site=STEP_SITES["spec"], prompt=full_prompt)
            spec_file.write_text(spec_text, encoding="utf-8")
            log.append(f"✅ Spec 完成 → {spec_file.relative_to(root)}")

    finally:
        ctx.close()
        pw.stop()

    log.append("\n🎉 工作流完成。运行 workflow_execute 开始写代码。")
    return "\n".join(log)


def handle_workflow_execute(args: dict) -> str:
    root = project_root()
    spec_file = root / "STEP4_SPEC" / "spec.md"
    accept_file = root / "STEP3_ACCEPT" / "final_plan.md"

    if not spec_file.exists():
        return "❌ 未找到 STEP4_SPEC/spec.md，请先运行 workflow_run"

    spec = spec_file.read_text(encoding="utf-8")
    final_plan = accept_file.read_text(encoding="utf-8") if accept_file.exists() else ""
    out_dir = args.get("output_dir") or str(root / "PROJECT")

    return f"""# 实现指令

你是一个代码执行 Agent，任务是根据以下规格完整实现项目。

## 输出目录
所有文件创建在：`{out_dir}`

## 最终方案
{final_plan}

## 完整 Spec
{spec}

## 执行要求
1. 按照 Spec 创建完整目录结构
2. 编写全部源代码
3. 运行项目，验证无报错启动
4. 执行 Spec 中定义的测试
5. 自动修复错误，不要在第一个失败处停下
6. 输出最终结果

逐步执行，不要等待确认。
"""


def handle_workflow_status(_args: dict) -> str:
    root = project_root()
    files = [
        ("INPUT/demand.md",           "需求文件"),
        ("STEP1_PLAN/draft_v1.md",    "Step 1 — 规划"),
        ("STEP2_REVIEW/review_v1.md", "Step 2 — 审查"),
        ("STEP3_ACCEPT/final_plan.md","Step 3 — 验收"),
        ("STEP4_SPEC/spec.md",        "Step 4 — Spec"),
    ]
    lines = [f"项目根目录：{root}\n"]
    for rel, label in files:
        p = root / rel
        if p.exists():
            lines.append(f"✅ {label:18s}  {rel}  ({p.stat().st_size:,} 字节)")
        else:
            lines.append(f"❌ {label:18s}  {rel}  （未生成）")
    return "\n".join(lines)


def handle_workflow_reset(args: dict) -> str:
    if not args.get("confirm"):
        return "请传入 confirm=true 确认删除"
    root = project_root()
    targets = [
        "STEP1_PLAN/draft_v1.md",
        "STEP2_REVIEW/review_v1.md",
        "STEP3_ACCEPT/final_plan.md",
        "STEP4_SPEC/spec.md",
    ]
    removed = []
    for rel in targets:
        p = root / rel
        if p.exists():
            p.unlink()
            removed.append(rel)
    return ("🗑️  已删除：\n" + "\n".join(f"  {r}" for r in removed)) if removed else "目录已经是干净的"


def handle_git_commit(args: dict) -> str:
    root = project_root()
    msg = args.get("message", "workflow step completed")
    try:
        subprocess.run(["git", "init"],      cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "add", "."],  cwd=root, check=True, capture_output=True)
        r = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=root, check=True, capture_output=True, text=True
        )
        return f"✅ 已提交：{msg}\n{r.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"❌ Git 错误：{e.stderr.strip() if e.stderr else str(e)}"


HANDLERS = {
    "workflow_run":     handle_workflow_run,
    "workflow_execute": handle_workflow_execute,
    "workflow_status":  handle_workflow_status,
    "workflow_reset":   handle_workflow_reset,
    "git_commit":       handle_git_commit,
}

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method", "")

        if method == "initialize":
            respond(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ai-workflow-mcp-browser", "version": "1.0.0"}
            })
        elif method == "initialized":
            pass
        elif method == "tools/list":
            respond(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            params   = req.get("params", {})
            name     = params.get("name", "")
            tool_args = params.get("arguments", {})
            handler  = HANDLERS.get(name)
            if handler:
                try:
                    text = handler(tool_args)
                except Exception as exc:
                    text = f"❌ {name} 执行出错：{exc}"
                respond(req_id, {"content": [{"type": "text", "text": text}]})
            else:
                error_response(req_id, -32601, f"未知工具：{name}")
        elif method == "ping":
            respond(req_id, {})

if __name__ == "__main__":
    main()
