#!/usr/bin/env python3
"""
AST-based documentation generator for the Exa Python SDK.

This script parses the SDK source code using Python's AST module and generates
markdown documentation for the specified methods and classes. It extracts:
- Method signatures with type hints
- Docstrings (Google-style)
- Parameter descriptions
- Return type information

Usage:
    python scripts/generate_docs.py > docs/python-sdk-reference.md

Author: Devin AI
"""

import ast
import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Methods to export for documentation (non-deprecated public API)
EXPORT_METHODS = {
    "Exa": [
        "search",
        "find_similar",
        "get_contents",
        "answer",
        "stream_answer",
    ],
    "AsyncExa": [
        "search",
        "find_similar",
        "get_contents",
        "answer",
        "stream_answer",
    ],
}

# TypedDicts to document
EXPORT_TYPEDDICTS = [
    "TextContentsOptions",
    "SummaryContentsOptions",
    "HighlightsContentsOptions",
    "ContextContentsOptions",
    "ExtrasOptions",
    "ContentsOptions",
]

# Dataclasses/Result types to document
EXPORT_DATACLASSES = [
    "Result",
    "SearchResponse",
    "AnswerResponse",
    "AnswerResult",
]


@dataclass
class ParsedParam:
    """Represents a parsed parameter from a function signature."""
    name: str
    type_hint: Optional[str]
    default: Optional[str]
    description: Optional[str] = None


@dataclass
class ParsedMethod:
    """Represents a parsed method with its signature and docstring."""
    name: str
    params: list[ParsedParam]
    return_type: Optional[str]
    docstring: Optional[str]
    is_async: bool = False


@dataclass
class ParsedClass:
    """Represents a parsed class (TypedDict or dataclass)."""
    name: str
    docstring: Optional[str]
    fields: list[tuple[str, str, Optional[str]]]  # (name, type, description)


def get_type_annotation_str(node: ast.expr) -> str:
    """Convert an AST type annotation node to a string representation."""
    if node is None:
        return "Any"
    return ast.unparse(node)


def parse_google_docstring(docstring: str) -> dict:
    """Parse a Google-style docstring into sections."""
    if not docstring:
        return {}
    
    sections = {}
    current_section = "description"
    current_content = []
    
    lines = docstring.strip().split("\n")
    
    for line in lines:
        stripped = line.strip()
        
        # Check for section headers
        if stripped.endswith(":") and stripped[:-1] in ["Args", "Returns", "Raises", "Example", "Examples", "Attributes"]:
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = stripped[:-1].lower()
            current_content = []
        else:
            current_content.append(line)
    
    if current_content:
        sections[current_section] = "\n".join(current_content).strip()
    
    return sections


def parse_args_section(args_text: str) -> dict[str, str]:
    """Parse the Args section of a docstring into parameter descriptions."""
    params = {}
    current_param = None
    current_desc = []
    
    for line in args_text.split("\n"):
        # Match parameter definition: "param_name (type): description"
        match = re.match(r"^\s*(\w+)\s*\([^)]*\):\s*(.*)$", line)
        if match:
            if current_param:
                params[current_param] = " ".join(current_desc).strip()
            current_param = match.group(1)
            current_desc = [match.group(2)] if match.group(2) else []
        elif current_param and line.strip():
            current_desc.append(line.strip())
    
    if current_param:
        params[current_param] = " ".join(current_desc).strip()
    
    return params


def parse_function_def(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ParsedMethod:
    """Parse a function definition node into a ParsedMethod."""
    params = []
    
    # Get docstring
    docstring = ast.get_docstring(node)
    parsed_doc = parse_google_docstring(docstring) if docstring else {}
    param_descriptions = parse_args_section(parsed_doc.get("args", "")) if "args" in parsed_doc else {}
    
    # Parse parameters
    args = node.args
    defaults = args.defaults
    num_defaults = len(defaults)
    num_args = len(args.args)
    
    for i, arg in enumerate(args.args):
        if arg.arg == "self":
            continue
        
        type_hint = get_type_annotation_str(arg.annotation) if arg.annotation else None
        
        # Calculate default value index
        default_idx = i - (num_args - num_defaults)
        default = None
        if default_idx >= 0:
            default = ast.unparse(defaults[default_idx])
        
        params.append(ParsedParam(
            name=arg.arg,
            type_hint=type_hint,
            default=default,
            description=param_descriptions.get(arg.arg),
        ))
    
    # Parse keyword-only arguments
    kw_defaults = args.kw_defaults
    for i, arg in enumerate(args.kwonlyargs):
        type_hint = get_type_annotation_str(arg.annotation) if arg.annotation else None
        default = ast.unparse(kw_defaults[i]) if kw_defaults[i] else None
        
        params.append(ParsedParam(
            name=arg.arg,
            type_hint=type_hint,
            default=default,
            description=param_descriptions.get(arg.arg),
        ))
    
    # Get return type
    return_type = get_type_annotation_str(node.returns) if node.returns else None
    
    return ParsedMethod(
        name=node.name,
        params=params,
        return_type=return_type,
        docstring=docstring,
        is_async=isinstance(node, ast.AsyncFunctionDef),
    )


def parse_class_def(node: ast.ClassDef) -> ParsedClass:
    """Parse a class definition node into a ParsedClass."""
    docstring = ast.get_docstring(node)
    parsed_doc = parse_google_docstring(docstring) if docstring else {}
    attr_descriptions = parse_args_section(parsed_doc.get("attributes", "")) if "attributes" in parsed_doc else {}
    
    fields = []
    
    for item in node.body:
        # Handle annotated assignments (TypedDict fields)
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            field_name = item.target.id
            field_type = get_type_annotation_str(item.annotation)
            field_desc = attr_descriptions.get(field_name)
            fields.append((field_name, field_type, field_desc))
    
    return ParsedClass(
        name=node.name,
        docstring=docstring,
        fields=fields,
    )


def generate_method_markdown(method: ParsedMethod, class_name: str) -> str:
    """Generate markdown documentation for a method."""
    lines = []
    
    # Method header
    async_prefix = "async " if method.is_async else ""
    lines.append(f"### `{async_prefix}{class_name}.{method.name}()`")
    lines.append("")
    
    # Description from docstring
    if method.docstring:
        parsed_doc = parse_google_docstring(method.docstring)
        if "description" in parsed_doc:
            lines.append(parsed_doc["description"])
            lines.append("")
    
    # Signature
    lines.append("**Signature:**")
    lines.append("```python")
    
    param_strs = []
    for param in method.params:
        param_str = param.name
        if param.type_hint:
            param_str += f": {param.type_hint}"
        if param.default is not None:
            param_str += f" = {param.default}"
        param_strs.append(param_str)
    
    params_formatted = ",\n    ".join(param_strs)
    if params_formatted:
        params_formatted = "\n    " + params_formatted + "\n"
    
    return_annotation = f" -> {method.return_type}" if method.return_type else ""
    lines.append(f"{async_prefix}def {method.name}({params_formatted}){return_annotation}")
    lines.append("```")
    lines.append("")
    
    # Parameters table
    if method.params:
        lines.append("**Parameters:**")
        lines.append("")
        lines.append("| Parameter | Type | Default | Description |")
        lines.append("|-----------|------|---------|-------------|")
        
        for param in method.params:
            type_str = f"`{param.type_hint}`" if param.type_hint else "-"
            default_str = f"`{param.default}`" if param.default is not None else "-"
            desc_str = param.description or "-"
            lines.append(f"| `{param.name}` | {type_str} | {default_str} | {desc_str} |")
        
        lines.append("")
    
    # Returns
    if method.return_type:
        lines.append("**Returns:**")
        lines.append(f"`{method.return_type}`")
        lines.append("")
    
    return "\n".join(lines)


def generate_class_markdown(cls: ParsedClass) -> str:
    """Generate markdown documentation for a TypedDict or dataclass."""
    lines = []
    
    lines.append(f"### `{cls.name}`")
    lines.append("")
    
    # Description from docstring
    if cls.docstring:
        parsed_doc = parse_google_docstring(cls.docstring)
        if "description" in parsed_doc:
            lines.append(parsed_doc["description"])
            lines.append("")
    
    # Fields table
    if cls.fields:
        lines.append("**Fields:**")
        lines.append("")
        lines.append("| Field | Type | Description |")
        lines.append("|-------|------|-------------|")
        
        for name, type_hint, desc in cls.fields:
            desc_str = desc or "-"
            lines.append(f"| `{name}` | `{type_hint}` | {desc_str} |")
        
        lines.append("")
    
    return "\n".join(lines)


def parse_sdk_file(filepath: Path) -> tuple[dict[str, list[ParsedMethod]], list[ParsedClass]]:
    """Parse the SDK file and extract methods and classes."""
    with open(filepath, "r") as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    methods_by_class: dict[str, list[ParsedMethod]] = {}
    classes: list[ParsedClass] = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            
            # Check if this is a class we want to document methods from
            if class_name in EXPORT_METHODS:
                methods_dict = {}  # Use dict to dedupe overloaded methods (keep last)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name in EXPORT_METHODS[class_name]:
                            # Check if this is an overload decorator (skip those)
                            is_overload = any(
                                isinstance(d, ast.Name) and d.id == "overload"
                                for d in item.decorator_list
                            )
                            if not is_overload:
                                methods_dict[item.name] = parse_function_def(item)
                # Preserve order from EXPORT_METHODS
                methods = [methods_dict[name] for name in EXPORT_METHODS[class_name] if name in methods_dict]
                methods_by_class[class_name] = methods
            
            # Check if this is a TypedDict or dataclass we want to document
            if class_name in EXPORT_TYPEDDICTS or class_name in EXPORT_DATACLASSES:
                classes.append(parse_class_def(node))
    
    return methods_by_class, classes


def generate_getting_started_section() -> str:
    """Generate the Getting Started section with UV/PIP installation tabs."""
    return '''## Getting Started

### Installation

<Tabs>
  <Tab title="uv">
    ```bash
    uv add exa-py
    ```
  </Tab>
  <Tab title="pip">
    ```bash
    pip install exa-py
    ```
  </Tab>
</Tabs>

### Basic Usage

```python
from exa_py import Exa

# Initialize the client
exa = Exa(api_key="your-api-key")

# Or use the EXA_API_KEY environment variable
exa = Exa()

# Perform a search
results = exa.search("latest AI research papers")

# Search with content retrieval
results = exa.search(
    "machine learning tutorials",
    contents={"text": {"max_characters": 1000}}
)

# Find similar pages
similar = exa.find_similar("https://example.com/article")
```

### Async Usage

```python
import asyncio
from exa_py import AsyncExa

async def main():
    exa = AsyncExa(api_key="your-api-key")
    results = await exa.search("async search example")
    print(results)

asyncio.run(main())
```

'''


def generate_full_documentation(filepath: Path) -> str:
    """Generate the full markdown documentation."""
    methods_by_class, classes = parse_sdk_file(filepath)
    
    lines = []
    
    # Header
    lines.append("---")
    lines.append("title: Python SDK Reference")
    lines.append("description: Auto-generated reference documentation for the Exa Python SDK")
    lines.append("---")
    lines.append("")
    lines.append("# Python SDK Reference")
    lines.append("")
    lines.append("This reference documentation is auto-generated from the SDK source code.")
    lines.append("")
    
    # Getting Started section
    lines.append(generate_getting_started_section())
    
    # Exa class methods
    if "Exa" in methods_by_class:
        lines.append("## Exa Client")
        lines.append("")
        lines.append("The synchronous Exa client for making API requests.")
        lines.append("")
        
        for method in methods_by_class["Exa"]:
            lines.append(generate_method_markdown(method, "Exa"))
    
    # AsyncExa class methods
    if "AsyncExa" in methods_by_class:
        lines.append("## AsyncExa Client")
        lines.append("")
        lines.append("The asynchronous Exa client for making API requests.")
        lines.append("")
        
        for method in methods_by_class["AsyncExa"]:
            lines.append(generate_method_markdown(method, "AsyncExa"))
    
    # TypedDicts
    typeddict_classes = [c for c in classes if c.name in EXPORT_TYPEDDICTS]
    if typeddict_classes:
        lines.append("## Content Options")
        lines.append("")
        lines.append("TypedDict classes for configuring content retrieval options.")
        lines.append("")
        
        for cls in typeddict_classes:
            lines.append(generate_class_markdown(cls))
    
    # Result types
    result_classes = [c for c in classes if c.name in EXPORT_DATACLASSES]
    if result_classes:
        lines.append("## Response Types")
        lines.append("")
        lines.append("Dataclasses representing API response objects.")
        lines.append("")
        
        for cls in result_classes:
            lines.append(generate_class_markdown(cls))
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    # Find the SDK file
    script_dir = Path(__file__).parent
    sdk_file = script_dir.parent / "exa_py" / "api.py"
    
    if not sdk_file.exists():
        print(f"Error: SDK file not found at {sdk_file}", file=sys.stderr)
        sys.exit(1)
    
    # Generate documentation
    docs = generate_full_documentation(sdk_file)
    print(docs)


if __name__ == "__main__":
    main()
