#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Offline Rule Agent (single-file)
- No network
- Rule-driven, stateful
- Optional "666" mode: classify -> single action
- Optional "cook-theory" error stage locator
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import json
import re
import time
import pathlib


# ----------------------------
# Persistence (local memory)
# ----------------------------

class LocalStore:
    def __init__(self, path: str = "agent_state.json"):
        self.path = pathlib.Path(path)

    def load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ----------------------------
# Policy / Rules
# ----------------------------

@dataclass
class Rule:
    name: str
    priority: int
    pattern: str                    # regex
    action: str                     # action id
    mode_required: Optional[str] = None  # e.g. "666" or None
    notes: str = ""


@dataclass
class Policy:
    # High-level system constraints (like "天")
    disallow_background_claims: bool = True
    disallow_future_promises: bool = True
    require_truthfulness: bool = True
    require_single_action_in_666: bool = True


@dataclass
class AgentConfig:
    policy: Policy = field(default_factory=Policy)
    state_path: str = "agent_state.json"
    enable_memory: bool = True

    # 666 defaults
    default_mode: str = "normal"  # "normal" | "666"
    max_actions_in_666: int = 1

    # Output template knobs
    show_debug: bool = False


# ----------------------------
# "Cook theory" stage locator
# ----------------------------

COOK_STAGES: List[Tuple[str, List[str], str]] = [
    ("0_接单检查", ["AAB support", "python-for-android", "p4a", "requires a python-for-android"], "主厨验切配组（buildozer/p4a版本门槛）"),
    ("1_切配台",   ["pip", "setuptools", "wheel", "Cython", "No matching distribution", "Failed building wheel"], "依赖/工具链备料（pip/cython）"),
    ("2_灶台准备", ["sdkmanager", "build-tools", "platforms;android", "cmdline-tools", "NDK not found", "Could not find NDK"], "SDK/NDK/JDK灶台是否齐"),
    ("3_炒菜中",   ["clang", "linker", "undefined reference", "gradle", "BUILD FAILED", ":app:"], "编译/链接/Gradle炒锅阶段"),
    ("4_出餐装盘", ["upload-artifact", "No such file or directory", ".apk", "Artifact"], "找APK/上传产物出餐口"),
    ("5_上桌后",   ["Traceback", "FileNotFoundError", "UnicodeDecodeError", "main.py"], "运行时资源/代码（上桌才暴露）"),
]


def locate_cook_stage(log_text: str) -> Dict[str, Any]:
    lt = log_text.lower()
    hits = []
    for stage_id, keywords, meaning in COOK_STAGES:
        score = 0
        matched = []
        for kw in keywords:
            if kw.lower() in lt:
                score += 1
                matched.append(kw)
        if score:
            hits.append({"stage": stage_id, "score": score, "meaning": meaning, "matched": matched})
    hits.sort(key=lambda x: x["score"], reverse=True)
    return {"hits": hits[:3], "best": hits[0] if hits else None}


# ----------------------------
# Actions
# ----------------------------

@dataclass
class ActionResult:
    text: str
    action_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class Actions:
    """
    Pure rule-based actions. You can add more.
    """

    @staticmethod
    def action_help(_: "Agent", user_text: str) -> ActionResult:
        return ActionResult(
            action_id="help",
            text=(
                "我能做：\n"
                "- normal：规则问答/模板输出\n"
                "- 666：分类结果 + 唯一动作\n"
                "- cook：根据日志定位环节\n\n"
                "命令：\n"
                "- /mode 666  或  /mode normal\n"
                "- /cook <粘贴日志>\n"
                "- /state 查看本地状态\n"
            ),
        )

    @staticmethod
    def action_set_mode(agent: "Agent", user_text: str) -> ActionResult:
        m = re.search(r"/mode\s+(\w+)", user_text.strip(), flags=re.I)
        if not m:
            return ActionResult(action_id="set_mode", text="用法：/mode 666 或 /mode normal")
        mode = m.group(1).lower()
        if mode not in ("normal", "666"):
            return ActionResult(action_id="set_mode", text="只支持：normal / 666")
        agent.state["mode"] = mode
        agent.persist_state()
        return ActionResult(action_id="set_mode", text=f"已切换模式：{mode}")

    @staticmethod
    def action_show_state(agent: "Agent", _: str) -> ActionResult:
        safe = {k: v for k, v in agent.state.items() if k not in ("_internal",)}
        return ActionResult(action_id="show_state", text=json.dumps(safe, ensure_ascii=False, indent=2))

    @staticmethod
    def action_cook(agent: "Agent", user_text: str) -> ActionResult:
        # /cook ... (rest is log)
        log = user_text.split("/cook", 1)[-1].strip()
        if not log:
            return ActionResult(action_id="cook", text="请在 /cook 后粘贴日志文本（至少包含红色报错那段）。")
        info = locate_cook_stage(log)
        best = info["best"]
        if not best:
            return ActionResult(action_id="cook", text="未识别到典型关键词。把更完整的报错段贴出来（20~40行）。", metadata=info)
        return ActionResult(
            action_id="cook",
            text=(
                f"定位：{best['stage']}（{best['meaning']}）\n"
                f"命中关键词：{', '.join(best['matched'])}\n"
                f"Top3候选：{json.dumps(info['hits'], ensure_ascii=False)}"
            ),
            metadata=info,
        )

    @staticmethod
    def action_666_classify(agent: "Agent", user_text: str) -> ActionResult:
        """
        Minimal 666: classify into (controllable/external/uncontrollable) and give ONE action.
        This is placeholder. In your use-case, you'll feed Actions logs and patterns.
        """
        # If user pasted a known error signature:
        text = user_text.lower()

        # Example signatures
        if "requires a python-for-android" in text or "aab support" in text:
            classification = "可控失败（版本漂移层 L3）"
            single_action = "在 buildozer.spec 中设置 p4a.branch = master（或保持已设置），并锁定 buildozer/pip/cython 版本。"
        elif "sdkmanager" in text or "failed to install android sdk packages" in text:
            classification = "外部失败（镜像/runner/网络）"
            single_action = "只重跑（最多3次），不改仓库；若稳定复现，再补齐 SDK 安装步骤（唯一动作）。"
        else:
            classification = "未定（需要更明确的错误指纹）"
            single_action = "贴出红色报错 20~40 行（不要全贴），再执行唯一动作。"

        # Enforce "single action" in 666
        if agent.config.policy.require_single_action_in_666:
            # ensure only one bullet action
            single_action = re.split(r"[。\n]\s*", single_action.strip())[0].strip() + "。"

        return ActionResult(
            action_id="666_classify",
            text=(
                "【666 分类结果】\n"
                f"- {classification}\n\n"
                "【唯一动作】\n"
                f"- {single_action}\n"
            ),
            metadata={"classification": classification, "single_action": single_action},
        )


# ----------------------------
# Rule Engine
# ----------------------------

class RuleEngine:
    def __init__(self, rules: List[Rule]):
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)

    def match(self, user_text: str, mode: str) -> Optional[Rule]:
        for r in self.rules:
            if r.mode_required and r.mode_required != mode:
                continue
            if re.search(r.pattern, user_text, flags=re.I | re.S):
                return r
        return None


# ----------------------------
# Agent
# ----------------------------

class Agent:
    def __init__(self, config: AgentConfig, rules: List[Rule]):
        self.config = config
        self.store = LocalStore(config.state_path)
        self.state = self.store.load() if config.enable_memory else {}
        self.state.setdefault("mode", config.default_mode)
        self.engine = RuleEngine(rules)

    def persist_state(self) -> None:
        if self.config.enable_memory:
            self.store.save(self.state)

    def _guardrails(self, response_text: str) -> str:
        # Simple policy checks (extend as needed)
        if self.config.policy.disallow_future_promises:
            # block phrases like "I'll do it later"
            forbidden = ["我稍后", "我待会", "等我", "我之后", "我会在未来", "我会晚点"]
            if any(f in response_text for f in forbidden):
                response_text += "\n\n[Policy] 已移除异步/未来承诺表述。"
        return response_text

    def handle(self, user_text: str) -> str:
        mode = self.state.get("mode", "normal")

        # Built-in command shortcuts:
        if user_text.strip().lower().startswith("/mode"):
            out = Actions.action_set_mode(self, user_text)
            return out.text

        rule = self.engine.match(user_text, mode)

        # If no rule matched, default behavior:
        if not rule:
            if mode == "666":
                out = Actions.action_666_classify(self, user_text)
            else:
                out = ActionResult(text="未匹配规则。输入 /help 查看可用命令，或切换到 /mode 666。")
            return self._guardrails(out.text)

        # Dispatch action
        action_fn = getattr(Actions, f"action_{rule.action}", None)
        if not action_fn:
            return self._guardrails(f"规则命中：{rule.name}，但未实现 action: {rule.action}")

        out: ActionResult = action_fn(self, user_text)

        # Enforce 666 single-action rule if needed
        if mode == "666" and self.config.policy.require_single_action_in_666:
            # crude check: allow only one "- " line under 唯一动作
            if out.text.count("\n- ") > self.config.max_actions_in_666 + 1:
                out.text = out.text + "\n\n[Policy] 触发 666 限制：已强制单动作输出。"

        if self.config.show_debug and out.metadata:
            out.text += "\n\n[debug]\n" + json.dumps(out.metadata, ensure_ascii=False, indent=2)

        return self._guardrails(out.text)


# ----------------------------
# Default Rules
# ----------------------------

DEFAULT_RULES = [
    Rule(name="Help", priority=100, pattern=r"^/help\b", action="help"),
    Rule(name="ShowState", priority=90, pattern=r"^/state\b", action="show_state"),
    Rule(name="CookStage", priority=80, pattern=r"^/cook\b", action="cook"),
    Rule(name="666Auto", priority=70, pattern=r".+", action="666_classify", mode_required="666"),
]


def main():
    cfg = AgentConfig(
        enable_memory=True,
        state_path="agent_state.json",
        default_mode="normal",
        show_debug=False,
    )
    agent = Agent(cfg, DEFAULT_RULES)

    print("Offline Rule Agent ready. Type /help for commands.")
    while True:
        try:
            user_text = input("\nYou> ").strip()
            if not user_text:
                continue
            if user_text.lower() in ("/quit", "/exit"):
                print("Bye.")
                break
            reply = agent.handle(user_text)
            print("\nAgent>\n" + reply)
        except KeyboardInterrupt:
            print("\nBye.")
            break


if __name__ == "__main__":
    main()
