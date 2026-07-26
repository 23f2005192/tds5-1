from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import re

app = FastAPI()


class Step(BaseModel):
    step_number: int
    tool: str
    args: Dict[str, Any]
    tokens_used: int


class RequestModel(BaseModel):
    budget_tokens: int
    steps: List[Step]


def normalize(obj):
    """
    Canonicalize arguments:
      - remove client_ts
      - sort dictionary keys
      - normalize whitespace in strings
    """
    if isinstance(obj, dict):
        return {
            k: normalize(v)
            for k, v in sorted(obj.items())
            if k != "client_ts"
        }

    if isinstance(obj, list):
        return [normalize(v) for v in obj]

    if isinstance(obj, str):
        return " ".join(obj.split())

    return obj


def same_call(a: Step, b: Step):
    return (
        a.tool == b.tool
        and normalize(a.args) == normalize(b.args)
    )


@app.post("/decision")
def decide(req: RequestModel):

    total = sum(s.tokens_used for s in req.steps)

    if total >= req.budget_tokens:
        return {
            "decision": "halt",
            "reason": f"Cumulative tokens_used ({total}) has reached the budget ({req.budget_tokens})."
        }

    steps = req.steps

    #
    # Detect AAA...
    #

    count = 1

    for i in range(len(steps)-2, -1, -1):

        if same_call(steps[i], steps[i+1]):
            count += 1
        else:
            break

    if count >= 3:
        return {
            "decision": "halt",
            "reason": "Detected repeated identical tool calls."
        }

    #
    # Detect ABABAB
    #

    if len(steps) >= 6:

        last = steps[-6:]

        A = last[0]
        B = last[1]

        cycle = True

        for i in range(6):

            expected = A if i % 2 == 0 else B

            if not same_call(last[i], expected):
                cycle = False
                break

        if cycle:
            return {
                "decision": "halt",
                "reason": "Detected repeating two-step tool cycle."
            }

    return {
        "decision": "continue",
        "reason": "Budget available and no looping pattern detected."
    }
