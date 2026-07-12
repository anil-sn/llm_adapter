"""
Tool ID deduplication utilities for Mistral and other models with strict ID validation.

This module provides utilities to sanitize and deduplicate tool IDs to meet
strict validation requirements (e.g., Mistral's 9-char alphanumeric-only rule).

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import secrets
import string

_ID_CHARS = string.ascii_letters + string.digits


class _IdDeduplicationContext:
    """Context for tracking and deduplicating tool IDs within a single request."""

    def __init__(self) -> None:
        self.seen_ids: set[str] = set()
        self.id_mappings: dict[str, list[str]] = {}
        self.result_index: dict[str, int] = {}


def _sanitize_tool_id_for_mistral(tool_id: str) -> str:
    """
    Sanitize tool ID to meet Mistral's strict validation rules.

    Mistral requires:
    - Exactly 9 characters
    - Only a-z, A-Z, 0-9 (no underscores, no hyphens)

    Strategy:
    - Use hash-based approach to maintain uniqueness
    - Take first 4 chars (prefix) + last 5 chars from base62 hash
    - Ensures collision resistance even for similar IDs

    Examples:
        toolu_01ABC123  -> toulAB3Kx  (prefix + hash)
        toolu_01XYZ789  -> toulMN9Pq  (prefix + hash, different)
        call_readf1     -> callR7Km2  (prefix + hash)
    """
    import hashlib
    import base64

    # Remove all non-alphanumeric characters
    alphanumeric_only = ''.join(c for c in tool_id if c.isalnum())

    # Create a stable hash of the full original ID
    hash_bytes = hashlib.sha256(tool_id.encode()).digest()
    # Convert to base64 and keep only alphanumeric
    hash_b64 = base64.b64encode(hash_bytes).decode('ascii')
    hash_alphanum = ''.join(c for c in hash_b64 if c.isalnum())

    if len(alphanumeric_only) >= 9:
        # Use first 4 chars of cleaned ID + 5 chars from hash
        prefix = alphanumeric_only[:4]
        suffix = hash_alphanum[:5]
        return prefix + suffix
    else:
        # Pad short IDs with hash
        needed = 9 - len(alphanumeric_only)
        return alphanumeric_only + hash_alphanum[:needed]


def _deduplicate_tool_id(tool_id: str, ctx: _IdDeduplicationContext) -> str:
    """Deduplicate tool ID for OpenAI (unique per request).

    When a duplicate ID is detected, generates a new random ID (keeping
    the first 8 chars of the original if long enough) and records the
    mapping so that later tool_result messages can find the correct ID.

    CRITICAL FIX: Sanitizes tool IDs for Mistral's strict validation:
    - Removes underscores and non-alphanumeric chars
    - Ensures exactly 9 characters
    - Maintains deduplication logic to prevent duplicate IDs

    Args:
        tool_id: Original tool ID (may contain underscores, hyphens, etc.)
        ctx: Deduplication context tracking seen IDs

    Returns:
        Sanitized, unique 9-character alphanumeric ID
    """
    # Step 1: Sanitize for Mistral (9 chars, alphanumeric only)
    sanitized_id = _sanitize_tool_id_for_mistral(tool_id)

    # Step 2: Deduplicate if we've seen this sanitized ID before
    id_to_use = sanitized_id

    if sanitized_id in ctx.seen_ids:
        # Generate new 9-char random ID to avoid collision
        id_to_use = "".join(secrets.choice(_ID_CHARS) for _ in range(9))
        # Ensure uniqueness
        while id_to_use in ctx.seen_ids:
            id_to_use = "".join(secrets.choice(_ID_CHARS) for _ in range(9))

    ctx.seen_ids.add(id_to_use)

    # Step 3: Record mapping from original tool_id to sanitized version
    if tool_id not in ctx.id_mappings:
        ctx.id_mappings[tool_id] = []
    ctx.id_mappings[tool_id].append(id_to_use)

    return id_to_use


def _resolve_tool_result_id(tool_use_id: str, ctx: _IdDeduplicationContext) -> str:
    """Resolve the deduplicated ID for a tool_result reference.

    When a tool_result references a tool_use by ID, we need to find the
    corresponding sanitized/deduplicated ID that was used in the request.

    Args:
        tool_use_id: Original tool_use ID from the tool_result block
        ctx: Deduplication context with ID mappings

    Returns:
        The sanitized/deduplicated ID to use in the tool message
    """
    if tool_use_id in ctx.id_mappings:
        mappings = ctx.id_mappings[tool_use_id]
        idx = ctx.result_index.get(tool_use_id, 0)
        if idx < len(mappings):
            ctx.result_index[tool_use_id] = idx + 1
            return mappings[idx]
    return tool_use_id
