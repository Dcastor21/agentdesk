from typing import TypedDict


class AgentState(TypedDict):
    # ── input ──────────────────────────────────────────────
    topic: str

    # ── node outputs (populated in pipeline order) ─────────
    plan: str        # Planner
    research: str    # Researcher
    summary: str     # Summarizer
    critique: str    # Critic
    score: float     # Critic  (0–1; used for routing in F05)
    draft: str       # Writer
    final: str       # Editor
