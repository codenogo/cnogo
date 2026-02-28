"""Contract detection phase: signature snapshot and comparison.

Parses Python files using AST to extract current signatures, then compares
them against stored graph signatures to detect breaking changes.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from scripts.context.model import GraphNode, NodeLabel
from scripts.context.python_parser import _build_signature


def extract_current_signatures(file_path: str) -> dict[str, str]:
    """Parse a Python file and return {qualified_name: signature_str}.

    Qualified names:
    - Top-level functions: "function_name"
    - Methods: "ClassName.method_name"

    Returns empty dict if file doesn't exist or has syntax errors.
    """
    path = Path(file_path)
    if not path.exists():
        return {}

    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    if not source.strip():
        return {}

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return {}

    sigs: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qualified = f"{class_name}.{child.name}"
                    sigs[qualified] = _build_signature(child)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only include top-level functions (not methods already captured above)
            # We check if this is directly inside a class by walking the tree again
            # Instead: we track which function nodes are methods
            pass

    # Second pass: collect top-level functions only
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sigs[node.name] = _build_signature(node)

    return sigs


def _parse_signature_params(sig: str) -> tuple[list[str], str]:
    """Parse a signature string into (param_names, return_type).

    Returns (param_list, return_annotation) as strings for comparison.
    This is a best-effort parse for change classification.
    """
    # Extract params between outer parens
    match = re.match(r"def \w+\((.*)\)(?:\s*->\s*(.+))?$", sig.strip())
    if not match:
        return [], ""
    params_str = match.group(1) or ""
    return_type = (match.group(2) or "").strip()

    if not params_str.strip():
        return [], return_type

    # Split params (naive split on comma, ignoring nested brackets)
    params: list[str] = []
    depth = 0
    current = ""
    for ch in params_str:
        if ch in "([{":
            depth += 1
            current += ch
        elif ch in ")]}":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            params.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        params.append(current.strip())

    return params, return_type


def _classify_change(
    old_sig: str, new_sig: str
) -> str:
    """Classify the type of signature change between old and new.

    Returns one of: param_added, param_removed, default_changed,
    return_type_changed, signature_changed (catch-all).
    """
    old_params, old_return = _parse_signature_params(old_sig)
    new_params, new_return = _parse_signature_params(new_sig)

    # Check return type change
    if old_return != new_return and old_params == new_params:
        return "return_type_changed"

    # Strip param names for count comparison
    def _strip_default(p: str) -> str:
        return p.split("=")[0].strip()

    def _param_name(p: str) -> str:
        # Remove type annotation and default
        name = p.split(":")[0].split("=")[0].strip()
        return name.lstrip("*")

    old_names = [_param_name(p) for p in old_params]
    new_names = [_param_name(p) for p in new_params]

    # Check param added
    if len(new_params) > len(old_params):
        return "param_added"

    # Check param removed
    if len(new_params) < len(old_params):
        return "param_removed"

    # Same count — check for default changes
    for op, np in zip(old_params, new_params):
        old_has_default = "=" in op
        new_has_default = "=" in np
        if old_has_default or new_has_default:
            old_default = op.split("=", 1)[1].strip() if old_has_default else None
            new_default = np.split("=", 1)[1].strip() if new_has_default else None
            if old_default != new_default:
                return "default_changed"

    # Return type also changed alongside other changes
    if old_return != new_return:
        return "return_type_changed"

    return "signature_changed"


def compare_signatures(
    stored_nodes: list[GraphNode],
    current_sigs: dict[str, str],
) -> list[dict[str, Any]]:
    """Compare stored graph signatures against fresh AST output.

    For each stored node (FUNCTION or METHOD), looks up the corresponding
    qualified name in current_sigs and detects breaks.

    Args:
        stored_nodes: GraphNode list from the graph (must have .signature).
        current_sigs: Dict from extract_current_signatures() — qualified_name → sig_str.

    Returns:
        List of change dicts with keys:
            symbol, old_signature, new_signature, change_type
    """
    changes: list[dict[str, Any]] = []

    for node in stored_nodes:
        if node.label not in (NodeLabel.FUNCTION, NodeLabel.METHOD):
            continue

        old_sig = node.signature
        if not old_sig:
            continue

        # Build qualified lookup key
        if node.label == NodeLabel.METHOD and node.class_name:
            lookup_key = f"{node.class_name}.{node.name}"
        else:
            lookup_key = node.name

        if lookup_key not in current_sigs:
            # Symbol not present in current file — skip (deletion handled elsewhere)
            continue

        new_sig = current_sigs[lookup_key]
        if old_sig == new_sig:
            continue

        change_type = _classify_change(old_sig, new_sig)
        changes.append(
            {
                "symbol": lookup_key,
                "old_signature": old_sig,
                "new_signature": new_sig,
                "change_type": change_type,
            }
        )

    return changes
