import os
import pathlib
import re

from anthropic import AsyncAnthropic

from .state import AgentState

_PROMPTS_DIR = pathlib.Path(__file__).parent.parent / "prompts"
_CLIENT = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env
_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


def _render(name: str, **kwargs: str) -> str:
    """Load a prompt markdown file and substitute only the named variables.

    Using explicit str.replace instead of str.format_map so that curly braces
    in LLM outputs (JSON examples, citations, code) don't cause KeyErrors.
    """
    text = (_PROMPTS_DIR / f"{name}.md").read_text()
    for key, val in kwargs.items():
        text = text.replace(f"{{{key}}}", str(val))
    return text


async def _call(prompt: str) -> str:
    msg = await _CLIENT.messages.create(
        model=_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


async def planner(state: AgentState) -> dict:
    prompt = _render("planner", topic=state["topic"])
    return {"plan": await _call(prompt)}


async def researcher(state: AgentState) -> dict:
    prompt = _render("researcher", topic=state["topic"], plan=state["plan"])
    return {"research": await _call(prompt)}


async def summarizer(state: AgentState) -> dict:
    prompt = _render("summarizer", topic=state["topic"], research=state["research"])
    return {"summary": await _call(prompt)}


async def critic(state: AgentState) -> dict:
    prompt = _render("critic", topic=state["topic"], summary=state["summary"])
    response = await _call(prompt)
    match = re.search(r"SCORE:\s*([\d.]+)", response)
    score = float(match.group(1)) if match else 0.0
    critique = response[: match.start()].strip() if match else response
    return {"critique": critique, "score": score}


async def writer(state: AgentState) -> dict:
    prompt = _render(
        "writer",
        topic=state["topic"],
        summary=state["summary"],
        critique=state["critique"],
    )
    return {"draft": await _call(prompt)}


async def editor(state: AgentState) -> dict:
    prompt = _render("editor", topic=state["topic"], draft=state["draft"])
    return {"final": await _call(prompt)}
