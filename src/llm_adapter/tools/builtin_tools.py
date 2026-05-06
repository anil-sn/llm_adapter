"""
Built-in Tool Definitions

Provides commonly useful tools that don't require external APIs:
- Calculator
- Date/time
- Text processing

These tools are always available without additional dependencies.

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import logging
import math
import datetime
from typing import Any, Dict, List

logger = logging.getLogger("builtin-tools")


# Calculator tool definition
calculator_tool = {
    "name": "calculator",
    "description": (
        "Evaluate mathematical expressions. Supports basic arithmetic, "
        "exponentiation, square roots, trigonometry, and common math functions. "
        "Use this for precise calculations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')",
            },
        },
        "required": ["expression"],
    },
}


# DateTime tool definition
datetime_tool = {
    "name": "get_datetime",
    "description": (
        "Get current date and time information in various formats. "
        "Useful for answering questions about 'today', 'current time', etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone (e.g., 'UTC', 'US/Pacific', 'Europe/London'). Default: UTC",
                "default": "UTC",
            },
            "format": {
                "type": "string",
                "description": "Output format: 'iso', 'human', or custom strftime format. Default: 'human'",
                "default": "human",
            },
        },
        "required": [],
    },
}


def execute_calculator(expression: str) -> Dict[str, Any]:
    """
    Safely evaluate a mathematical expression.

    Args:
        expression: Math expression string

    Returns:
        Dictionary with result or error

    Example:
        >>> execute_calculator("2 + 2")
        {'success': True, 'result': 4.0, 'expression': '2 + 2'}
    """
    try:
        # Create safe namespace with math functions
        safe_namespace = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            # Math module functions
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "pi": math.pi,
            "e": math.e,
        }

        # Evaluate expression
        result = eval(expression, {"__builtins__": {}}, safe_namespace)

        logger.info(f"Calculator: '{expression}' = {result}")

        return {
            "success": True,
            "result": result,
            "expression": expression,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Calculator error for '{expression}': {e}")
        return {
            "success": False,
            "result": None,
            "expression": expression,
            "error": str(e),
        }


def execute_datetime(timezone: str = "UTC", format: str = "human") -> Dict[str, Any]:
    """
    Get current date/time information.

    Args:
        timezone: Timezone string (not fully implemented, uses UTC)
        format: Output format ('iso', 'human', or strftime format)

    Returns:
        Dictionary with datetime information

    Example:
        >>> execute_datetime(format="iso")
        {'success': True, 'datetime': '2026-05-06T04:00:00Z', ...}
    """
    try:
        now = datetime.datetime.now(datetime.timezone.utc)

        # Format output
        if format == "iso":
            formatted = now.isoformat()
        elif format == "human":
            formatted = now.strftime("%A, %B %d, %Y at %I:%M %p UTC")
        else:
            # Try custom strftime format
            formatted = now.strftime(format)

        return {
            "success": True,
            "datetime": formatted,
            "timestamp": now.timestamp(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": timezone,
            "error": None,
        }

    except Exception as e:
        logger.error(f"DateTime error: {e}")
        return {
            "success": False,
            "datetime": None,
            "error": str(e),
        }


def get_builtin_tools() -> List[Dict[str, Any]]:
    """
    Get all built-in tool definitions.

    Returns:
        List of tool definition dictionaries

    Example:
        >>> tools = get_builtin_tools()
        >>> print([t["name"] for t in tools])
        ['calculator', 'get_datetime']
    """
    return [calculator_tool, datetime_tool]


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a built-in tool by name.

    Args:
        tool_name: Name of the tool to execute
        **kwargs: Tool arguments

    Returns:
        Tool execution result

    Example:
        >>> execute_tool("calculator", expression="2 + 2")
        {'success': True, 'result': 4.0, ...}
    """
    if tool_name == "calculator":
        return execute_calculator(kwargs.get("expression", ""))
    elif tool_name == "get_datetime":
        return execute_datetime(
            kwargs.get("timezone", "UTC"),
            kwargs.get("format", "human"),
        )
    else:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
        }
