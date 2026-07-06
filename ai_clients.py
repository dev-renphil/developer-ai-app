import os

import anthropic
from google import genai
from openai import OpenAI


class AIClients:
    # TODO create an abstract class then a separate class for each AI
    def __init__(self):
        self._openai = None
        self._google = None
        self._claude = None

    @staticmethod
    def _require(var: str) -> str:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"{var} must be set in .env file")
        return value

    @property
    def openai(self) -> OpenAI:
        if self._openai is None:
            self._openai = OpenAI(api_key=self._require("OPENAI_API_KEY"))
        return self._openai

    @property
    def google(self) -> genai.Client:
        if self._google is None:
            self._google = genai.Client(api_key=self._require("GEMINI_API_KEY"))
        return self._google

    @property
    def claude(self) -> anthropic.Anthropic:
        if self._claude is None:
            self._claude = anthropic.Anthropic(api_key=self._require("CLAUDE_API_KEY"))
        return self._claude

    def init(self, use_ai: str) -> None:
        """Eagerly create the client for the configured AI provider at startup."""
        use_ai = use_ai.lower()
        if use_ai == "openai":
            _ = self.openai
        elif use_ai == "gemini":
            _ = self.google
        elif use_ai == "claude":
            _ = self.claude
        else:
            raise ValueError(f"Unknown USE_AI value: '{use_ai}'. Expected 'openai', 'gemini', or 'claude'.")