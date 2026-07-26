from fastapi import FastAPI
from pydantic import BaseModel
from guardrail import handle_request

app = FastAPI()

class Request(BaseModel):
    tool: str
    arguments: dict

@app.post("/")
def root(req: Request):
    return handle_request(req.tool, req.arguments)
