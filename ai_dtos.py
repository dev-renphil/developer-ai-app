from typing import Any
from urllib.parse import urlparse, parse_qs

from pydantic import BaseModel, Field


class Step1Reply(BaseModel):
    operation: str | None
    element_ids: list[str]
    image_process: bool
    text: str


class ReceiveDTO(BaseModel):
    user_message: Any
    history: Any
    session_id: Any
    receiving_url: Any
    topic: Any
    pre_test_results: list[Any] = Field(default_factory=list)

    def get_root_url_with_scheme(self):
        parsed_url = urlparse(self.receiving_url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"

    def get_query_params(self):
        return parse_qs(self.parsed_url.query)



Step2ExampleOutput = [
    {"id": "1", "changes": {"strokeColor": "#ff0000"}},
    {"id": "2", "changes": {"x": 50, "y": 150}},
    {"id": "3", "delete": True},
    {
        "id": "new_rect_1",
        "create": True,
        "type": "rectangle",
        "changes": {
            "x": 100,
            "y": 120,
            "width": 200,
            "height": 100,
            "strokeColor": "#1e1e1e",
            "backgroundColor": "transparent",
        },
    },
]

Step2ExampleElement = {
    "id": "kF0Mp1K-BetBmBdtNFJzJ",
    "type": "ellipse",
    "x": 1697.82275390625,
    "y": -1097.52490234375,
    "width": 1500.0,
    "height": 300.4,
    "angle": 0,
    "strokeColor": "#000000",
    "backgroundColor": "transparent",
}
