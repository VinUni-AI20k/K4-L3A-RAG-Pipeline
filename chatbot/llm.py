"""Dispatch a chat completion call to the configured LLM provider."""

import os

from . import config


class LLMError(RuntimeError):
    """Raised when the configured provider cannot produce an answer."""


def call_llm(system_prompt: str, user_message: str) -> str:
    provider = config.LLM_PROVIDER
    model = config.LLM_MODEL or config.DEFAULT_MODELS.get(provider, "")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("Thiếu OPENAI_API_KEY trong .env")
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content or ""

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMError("Thiếu GEMINI_API_KEY trong .env")
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=f"{system_prompt}\n\n{user_message}",
        )
        return response.text or ""

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMError("Thiếu ANTHROPIC_API_KEY trong .env")
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    raise LLMError(f"LLM_PROVIDER không hỗ trợ: {provider}")
