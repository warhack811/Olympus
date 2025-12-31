from typing import List, Tuple, Annotated, TypedDict, Union, Dict, Any
import operator


class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    intermediate_steps: Annotated[List[tuple], operator.add]


class AgentState(TypedDict):
    messages: Annotated[List[Any], operator.add]
    sender: str
