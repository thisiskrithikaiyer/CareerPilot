from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    # Conversation
    messages: Annotated[list, add_messages]
    user_id: str

    # Routing
    intent: str         
    agent: str         
    intake_complete: bool  
    phase: str          

    # User snapshot (populated by context_builder)
    days_since: int | None
    days_left: int | None
    mood_score: int | None        # 1-10 from last check-in
    energy_score: int | None      # 1-10 from last check-in
    open_tasks: int | None        # uncompleted plan items
    leetcode_level: str | None    # fundamentals | building | standard | advanced
    resume_text: str | None       # raw resume text (goal_planner / profile_builder only)
    linkedin_text: str | None     # raw linkedin text (goal_planner / profile_builder only)
    role: str | None              # SWE | MLE | AI Engineer | Data Engineer
    tracking_summary: dict | None # last 10 days of checkins + task completion (goal_planner only)
    tracking_skills: dict | None  # current skill set
    talent_map: dict | None       # structured skills graph from background talent_mapper
    
    # Response
    response: str
    sources: list[str]            # citations from RAG
    needs_plan_refresh: bool      # agent persisted progress/closed tasks → UI should refetch plan
    chips: list[str]              # structured chips from agent (replaces text-parsed CHIPS: hack)
    field_key: str | None         # intake: next field to collect

    # Agent routing events (populated by orchestrator, returned to UI)
    agent_events: list
