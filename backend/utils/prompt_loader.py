"""
Loads LLM prompt templates from the prompts/ directory and substitutes variables.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class PromptVariableMissingError(Exception):
    pass


def load_prompt(template_name: str, **kwargs: str) -> str:
    """
    Load a prompt template by name and substitute all {{variable}} placeholders.

    Args:
        template_name: Name of the .txt file without extension (e.g., "intent_extraction")
        **kwargs: Variable values to substitute

    Returns:
        Fully rendered prompt string

    Raises:
        FileNotFoundError: If the template doesn't exist
        PromptVariableMissingError: If a required variable is not provided
    """
    template_path = PROMPTS_DIR / f"{template_name}.txt"

    if not template_path.exists():
        raise FileNotFoundError(
            f"Prompt template '{template_name}' not found at {template_path}"
        )

    template = template_path.read_text(encoding="utf-8")

    # Find all variables
    variables = re.findall(r"\{\{(\w+)\}\}", template)

    # Check all variables are provided
    missing = [v for v in variables if v not in kwargs]
    if missing:
        raise PromptVariableMissingError(
            f"Template '{template_name}' requires variables: {missing}. "
            f"Got: {list(kwargs.keys())}"
        )

    # Substitute all variables
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    return template


if __name__ == "__main__":
    # Quick verification
    result = load_prompt("intent_extraction", user_prompt="Build a CRM with contacts and login")
    print("✅ Prompt loaded successfully:")
    print(result[:200] + "...")
