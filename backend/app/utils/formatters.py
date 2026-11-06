import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def format_session_to_markdown(
    session_title: str,
    system_prompt: Optional[str],
    messages: List[Dict[str, Any]],
    bot_name: str = "AI 助手",
) -> str:
    """将单个会话及对话列表格式化为美观且易读的 Markdown 文本"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_lines = [
        f"# {session_title}",
        f"> 导出时间: {now_str}",
    ]
    if system_prompt:
        md_lines.append(f"> 系统人设: {system_prompt}")
    md_lines.append("\n---\n")

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "") or ""
        m_time = msg.get("created_at")
        time_str = (
            f" ({datetime.fromtimestamp(m_time).strftime('%H:%M:%S')})"
            if m_time
            else ""
        )

        if role == "user":
            md_lines.append(f"### 👤 用户{time_str}\n\n{content}\n\n---\n")
        elif role == "assistant":
            header = f"### 🤖 {bot_name}{time_str}\n\n"
            body = ""
            if reasoning:
                quoted = "\n".join(f"> {line}" for line in reasoning.splitlines())
                body += f"> 💭 **思考过程**:\n{quoted}\n\n"
            body += f"{content}\n\n---\n"
            md_lines.append(header + body)
        else:
            md_lines.append(f"### ⚙️ {role.capitalize()}{time_str}\n\n{content}\n\n---\n")

    return "\n".join(md_lines)


def parse_markdown_to_messages(
    md_text: str,
) -> Tuple[str, Optional[str], List[Dict[str, str]]]:
    """解析 Markdown 格式的聊天记录，自动提取标题、系统人设以及分轮次对话消息"""
    lines = md_text.strip().splitlines()
    title = "导入的对话"
    system_prompt = None
    messages = []

    content_start_idx = 0
    for idx, line in enumerate(lines[:15]):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("### "):
            title = stripped[2:].strip()
            content_start_idx = idx + 1
            break

    for idx in range(content_start_idx, min(content_start_idx + 15, len(lines))):
        stripped = lines[idx].strip()
        if any(
            stripped.startswith(prefix)
            for prefix in ["> 模型人设:", "> 系统人设:", "> 系统设定:", "> System Prompt:"]
        ):
            system_prompt = stripped.split(":", 1)[1].strip()
            break

    role_pattern = re.compile(
        r"^(?:###\s*(👤[^\n]*|🤖[^\n]*|⚙️[^\n]*|(?:用户|User|Human|提问)[^\n]*|(?:助手|Assistant|AI|Bot|回答)[^\n]*)|##\s*(👤[^\n]*|🤖[^\n]*|(?:用户|User)[^\n]*|(?:助手|Assistant|AI)[^\n]*)|(?:\*\*|__)(用户|User|助手|Assistant)(?:\*\*|__)\s*[:：][^\n]*)\n?",
        re.IGNORECASE | re.MULTILINE,
    )

    matches = list(role_pattern.finditer(md_text))
    if not matches:
        if md_text.strip():
            messages.append(
                {"role": "user", "content": md_text.strip(), "reasoning_content": ""}
            )
        return title, system_prompt, messages

    for i in range(len(matches)):
        m = matches[i]
        matched_role_str = (m.group(1) or m.group(2) or m.group(3) or m.group(0)).lower()
        if "👤" in matched_role_str or any(keyword in matched_role_str for keyword in ["用户", "user", "human", "提问"]):
            role = "user"
        else:
            role = "assistant"

        start_pos = m.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        block_text = md_text[start_pos:end_pos].strip()

        block_text = re.sub(r"^(?:---|\*\*\*)\s*", "", block_text).strip()
        block_text = re.sub(r"\s*(?:---|\*\*\*)$", "", block_text).strip()

        reasoning_content = ""
        reasoning_match = re.search(
            r"> (?:💭\s*)?(?:\*\*)?(?:思考过程|Reasoning)(?:\*\*)?\s*:\s*\n((?:>.*(?:\n|$))+)",
            block_text,
        )
        if reasoning_match:
            raw_lines = reasoning_match.group(1).splitlines()
            cleaned = "\n".join(
                line[1:].strip() if line.startswith(">") else line for line in raw_lines
            ).strip()
            reasoning_content = cleaned
            block_text = (
                block_text[: reasoning_match.start()]
                + block_text[reasoning_match.end() :]
            ).strip()

        if block_text or reasoning_content:
            messages.append(
                {
                    "role": role,
                    "content": block_text,
                    "reasoning_content": reasoning_content,
                }
            )

    return title, system_prompt, messages

