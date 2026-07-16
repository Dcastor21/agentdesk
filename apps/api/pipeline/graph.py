from langgraph.graph import END, StateGraph

from .nodes import critic, editor, planner, researcher, summarizer, writer
from .state import AgentState


def _build() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("planner", planner)
    g.add_node("researcher", researcher)
    g.add_node("summarizer", summarizer)
    g.add_node("critic", critic)
    g.add_node("writer", writer)
    g.add_node("editor", editor)

    g.set_entry_point("planner")
    g.add_edge("planner", "researcher")
    g.add_edge("researcher", "summarizer")
    g.add_edge("summarizer", "critic")
    g.add_edge("critic", "writer")   # F05 replaces with conditional edge
    g.add_edge("writer", "editor")
    g.add_edge("editor", END)

    return g.compile()  # F04 passes checkpointer= here


graph = _build()
