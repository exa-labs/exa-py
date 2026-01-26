#!/usr/bin/env python3
"""
AST-based documentation generator for the Exa Python SDK.

This script parses the SDK source code using Python's AST module and generates
markdown documentation for the specified methods and classes. It extracts:
- Method signatures with type hints
- Docstrings (Google-style) including Examples sections
- Parameter descriptions
- Return type information

Configuration is loaded from gen_config.json.

Usage:
    python scripts/generate_docs.py > docs/python-sdk-reference.md
"""

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


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
    examples: Optional[str] = None
    is_async: bool = False


@dataclass
class ParsedClass:
    """Represents a parsed class (TypedDict or dataclass)."""
    name: str
    docstring: Optional[str]
    fields: list[tuple[str, str, Optional[str]]]  # (name, type, description)


class DocGenerator:
    """Documentation generator that uses config file and extracts from code."""

    def __init__(self, config_path: Path):
        with open(config_path) as f:
            self.config = json.load(f)

        self.export_methods = self.config["export"]["methods"]
        self.export_research_methods = self.config["export"]["research_methods"]
        self.export_typeddicts = self.config["export"].get("typeddicts", [])
        # dataclasses list is now optional - if empty, we auto-discover all classes
        self.export_dataclasses = self.config["export"].get("dataclasses", [])
        self.getting_started = self.config["getting_started"]
        self.output_examples = self.config.get("output_examples", {})
        self.method_result_objects = self.config.get("method_result_objects", {})
        self.manual_types = self.config.get("manual_types", {})
        # Will be populated when parsing classes
        self.parsed_classes: Dict[str, ParsedClass] = {}
        # Start with manual types and explicitly listed types; auto-discovered classes added during parsing
        self.all_linkable_types: set = set(self.export_typeddicts) | set(self.export_dataclasses) | set(self.manual_types.keys())

    def get_type_annotation_str(self, node: ast.expr) -> str:
        """Convert an AST type annotation node to a string representation."""
        if node is None:
            return "Any"
        return ast.unparse(node)

    def escape_mdx_braces(self, text: str) -> str:
        """Escape curly braces in text for MDX compatibility."""
        if not text:
            return text
        pattern = r'(?<!`)(\{[^}`]+\})(?!`)'
        return re.sub(pattern, r'`\1`', text)

    def linkify_type(self, type_str: str) -> str:
        """Convert type references to markdown links where applicable."""
        if not type_str:
            return type_str

        result = type_str
        # Use all_linkable_types which includes both config and auto-discovered types
        for type_name in self.all_linkable_types:
            anchor = type_name.lower()
            # Negative lookahead for ](#  to avoid re-linking already linked types
            pattern = rf'\b{type_name}\b(?!\]\(#)'
            replacement = f'[{type_name}](#{anchor})'
            result = re.sub(pattern, replacement, result)

        return result

    def parse_google_docstring(self, docstring: str) -> dict:
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
                    # Strip trailing empty lines only, preserve leading indentation
                    while current_content and not current_content[-1].strip():
                        current_content.pop()
                    sections[current_section] = "\n".join(current_content)
                current_section = stripped[:-1].lower()
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            # Strip trailing empty lines only, preserve leading indentation
            while current_content and not current_content[-1].strip():
                current_content.pop()
            sections[current_section] = "\n".join(current_content)

        return sections

    def parse_args_section(self, args_text: str) -> dict[str, str]:
        """Parse the Args section of a docstring into parameter descriptions."""
        params = {}
        current_param = None
        current_desc = []

        for line in args_text.split("\n"):
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

    def extract_examples_from_docstring(self, docstring: str) -> Optional[str]:
        """Extract Examples section from docstring and format as code."""
        if not docstring:
            return None

        parsed = self.parse_google_docstring(docstring)
        examples_text = parsed.get("examples") or parsed.get("example")

        if not examples_text:
            return None

        # Clean up the examples - remove leading whitespace consistently
        lines = examples_text.split("\n")
        # Find minimum indentation (excluding empty lines)
        non_empty_lines = [l for l in lines if l.strip()]
        if not non_empty_lines:
            return None

        min_indent = min(len(l) - len(l.lstrip()) for l in non_empty_lines)
        cleaned_lines = []
        for l in lines:
            if len(l) >= min_indent:
                cleaned_lines.append(l[min_indent:])
            elif l.strip() == "":
                cleaned_lines.append("")
            else:
                cleaned_lines.append(l.lstrip())

        # Remove >>> prompts if present (doctest style)
        result_lines = []
        for line in cleaned_lines:
            stripped = line.strip()
            if stripped.startswith(">>>"):
                result_lines.append(stripped[3:].lstrip())
            elif stripped.startswith("..."):
                result_lines.append("    " + stripped[3:].lstrip())
            else:
                result_lines.append(line)

        # Remove trailing empty lines
        while result_lines and not result_lines[-1].strip():
            result_lines.pop()

        return "\n".join(result_lines)

    def parse_function_def(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> ParsedMethod:
        """Parse a function definition node into a ParsedMethod."""
        params = []

        docstring = ast.get_docstring(node)
        parsed_doc = self.parse_google_docstring(docstring) if docstring else {}
        param_descriptions = self.parse_args_section(parsed_doc.get("args", "")) if "args" in parsed_doc else {}

        # Extract examples from docstring
        examples = self.extract_examples_from_docstring(docstring)

        # Parse parameters
        args = node.args
        defaults = args.defaults
        num_defaults = len(defaults)
        num_args = len(args.args)

        for i, arg in enumerate(args.args):
            if arg.arg == "self":
                continue

            type_hint = self.get_type_annotation_str(arg.annotation) if arg.annotation else None

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
            type_hint = self.get_type_annotation_str(arg.annotation) if arg.annotation else None
            default = ast.unparse(kw_defaults[i]) if kw_defaults[i] else None

            params.append(ParsedParam(
                name=arg.arg,
                type_hint=type_hint,
                default=default,
                description=param_descriptions.get(arg.arg),
            ))

        return_type = self.get_type_annotation_str(node.returns) if node.returns else None

        return ParsedMethod(
            name=node.name,
            params=params,
            return_type=return_type,
            docstring=docstring,
            examples=examples,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

    def extract_pydantic_field_info(self, annotation: ast.expr) -> tuple[str, Optional[str]]:
        """Extract type and description from Pydantic Annotated[type, Field(...)] syntax.

        Returns:
            Tuple of (type_str, description or None)
        """
        # Check if it's Annotated[..., Field(...)]
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name) and annotation.value.id == "Annotated":
                if isinstance(annotation.slice, ast.Tuple) and len(annotation.slice.elts) >= 2:
                    # First element is the actual type
                    base_type = self.get_type_annotation_str(annotation.slice.elts[0])

                    # Look for Field() call in remaining elements
                    for elem in annotation.slice.elts[1:]:
                        if isinstance(elem, ast.Call):
                            # Check if it's a Field() call
                            func_name = ""
                            if isinstance(elem.func, ast.Name):
                                func_name = elem.func.id
                            elif isinstance(elem.func, ast.Attribute):
                                func_name = elem.func.attr

                            if func_name == "Field":
                                # Look for description keyword argument
                                for keyword in elem.keywords:
                                    if keyword.arg == "description":
                                        if isinstance(keyword.value, ast.Constant):
                                            return base_type, keyword.value.value

                    return base_type, None

        # Not an Annotated type, return as-is
        return self.get_type_annotation_str(annotation), None

    def parse_class_def(self, node: ast.ClassDef, all_class_nodes: Optional[dict] = None) -> ParsedClass:
        """Parse a class definition node into a ParsedClass."""
        docstring = ast.get_docstring(node)
        parsed_doc = self.parse_google_docstring(docstring) if docstring else {}
        attr_descriptions = self.parse_args_section(parsed_doc.get("attributes", "")) if "attributes" in parsed_doc else {}

        fields = []

        # First, collect fields from parent classes (for inheritance)
        if all_class_nodes:
            for base in node.bases:
                base_name = None
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr

                if base_name and base_name in all_class_nodes:
                    parent_node = all_class_nodes[base_name]
                    parent_class = self.parse_class_def(parent_node, all_class_nodes)
                    fields.extend(parent_class.fields)

        # Then collect fields from this class
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id

                # Try to extract from Pydantic Field() first
                field_type, pydantic_desc = self.extract_pydantic_field_info(item.annotation)

                # Use Pydantic description, fall back to docstring attributes
                field_desc = pydantic_desc or attr_descriptions.get(field_name)
                fields.append((field_name, field_type, field_desc))

        return ParsedClass(
            name=node.name,
            docstring=docstring,
            fields=fields,
        )

    def parse_sdk_file(self, filepath: Path, export_methods: Optional[dict] = None) -> tuple[dict[str, list[ParsedMethod]], list[ParsedClass]]:
        """Parse the SDK file and extract methods and classes."""
        if export_methods is None:
            export_methods = self.export_methods

        with open(filepath, "r") as f:
            source = f.read()

        tree = ast.parse(source)

        methods_by_class: dict[str, list[ParsedMethod]] = {}
        classes: list[ParsedClass] = []

        # First pass: collect all class definitions for inheritance lookup
        all_class_nodes: dict[str, ast.ClassDef] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                all_class_nodes[node.name] = node

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name

                if class_name in export_methods:
                    methods_dict = {}
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if item.name in export_methods[class_name]:
                                is_overload = any(
                                    isinstance(d, ast.Name) and d.id == "overload"
                                    for d in item.decorator_list
                                )
                                if not is_overload:
                                    methods_dict[item.name] = self.parse_function_def(item)
                    methods = [methods_dict[name] for name in export_methods[class_name] if name in methods_dict]
                    methods_by_class[class_name] = methods

                # Export classes that are:
                # 1. Explicitly listed in typeddicts or dataclasses config
                # 2. Auto-discovered (not client classes, not private unless explicitly listed)
                is_explicitly_listed = class_name in self.export_typeddicts or class_name in self.export_dataclasses
                is_client_class = class_name in (list(export_methods.keys()) + ["ResearchBaseClient"])

                if is_explicitly_listed or (not is_client_class and not class_name.startswith('_')):
                    parsed_class = self.parse_class_def(node, all_class_nodes)
                    classes.append(parsed_class)
                    # Auto-add to linkable types
                    self.all_linkable_types.add(class_name)

        return methods_by_class, classes

    def generate_getting_started_section(self) -> str:
        """Generate the Getting Started section with tabs."""
        api_key_url = self.getting_started.get("api_key_url", "https://dashboard.exa.ai/api-keys")
        return f'''## Getting started

Install the [exa-py](https://github.com/exa-labs/exa-py) SDK

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

and then instantiate an Exa client

```python
from exa_py import Exa

exa = Exa()  # Reads EXA_API_KEY from environment
# or explicitly: exa = Exa(api_key="your-api-key")
```

<Card
  title="Get API Key"
  icon="key"
  horizontal
  href="{api_key_url}"
>
  Follow this link to get your API key
</Card>

'''

    def generate_method_markdown(self, method: ParsedMethod, class_name: str, method_display_name: Optional[str] = None) -> str:
        """Generate markdown documentation for a method."""
        lines = []

        display_name = method_display_name or method.name

        # Determine the config key for examples/result objects
        if class_name == "ResearchClient":
            config_key = f"research.{method.name}"
            header_name = f"research.{display_name}"
        else:
            config_key = method.name
            header_name = display_name

        lines.append(f"## `{header_name}` Method")
        lines.append("")

        # Description from docstring
        if method.docstring:
            parsed_doc = self.parse_google_docstring(method.docstring)
            if "description" in parsed_doc:
                lines.append(self.escape_mdx_braces(parsed_doc["description"]))
                lines.append("")

        # Input Example section - from docstring Examples section
        lines.append("### Input Example")
        lines.append("")
        lines.append("```python")

        if method.examples:
            lines.append(method.examples)
        else:
            # Fallback: generate basic example
            if class_name == "ResearchClient":
                lines.append(f"result = exa.research.{method.name}(")
            else:
                lines.append(f"result = exa.{method.name}(")

            example_params = []
            for param in method.params:
                if param.default is None:
                    if param.type_hint and "str" in param.type_hint:
                        example_params.append(f'    {param.name}="example"')
                    else:
                        example_params.append(f"    {param.name}=...")
            if example_params:
                lines.append(",\n".join(example_params))
            lines.append(")")

        lines.append("```")
        lines.append("")

        # Input Parameters table
        if method.params:
            lines.append("### Input Parameters")
            lines.append("")
            lines.append("| Parameter | Type | Description | Default |")
            lines.append("| --------- | ---- | ----------- | ------- |")

            for param in method.params:
                type_str = self.linkify_type(param.type_hint) if param.type_hint else "Any"
                # Also linkify types mentioned in descriptions
                desc_str = self.escape_mdx_braces(param.description) if param.description else "-"
                desc_str = self.linkify_type(desc_str)
                if param.default is None:
                    default_str = "Required"
                elif param.default == "None":
                    default_str = "None"
                else:
                    default_str = f"`{param.default}`"
                lines.append(f"| {param.name} | {type_str} | {desc_str} | {default_str} |")

            lines.append("")

        # Return Example section (JSON output from config)
        output_example = self.output_examples.get(config_key)
        if output_example:
            lines.append("### Return Example")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(output_example, indent=2))
            lines.append("```")
            lines.append("")

        # Result Object table - extract fields from parsed class
        result_class_name = self.method_result_objects.get(config_key)

        if result_class_name and result_class_name in self.parsed_classes:
            result_class = self.parsed_classes[result_class_name]
            lines.append("### Result Object")
            lines.append("")
            lines.append("| Field | Type | Description |")
            lines.append("| ----- | ---- | ----------- |")
            for field_name, field_type, field_desc in result_class.fields:
                # Linkify types in the type column (no backticks so links work)
                linked_type = self.linkify_type(field_type)
                desc_str = self.escape_mdx_braces(field_desc) if field_desc else "-"
                lines.append(f"| {field_name} | {linked_type} | {desc_str} |")
            lines.append("")

        return "\n".join(lines)

    def generate_class_markdown(self, cls: ParsedClass) -> str:
        """Generate markdown documentation for a TypedDict or dataclass."""
        lines = []

        lines.append(f"#### `{cls.name}`")
        lines.append("")

        if cls.docstring:
            parsed_doc = self.parse_google_docstring(cls.docstring)
            if "description" in parsed_doc:
                lines.append(self.escape_mdx_braces(parsed_doc["description"]))
                lines.append("")

        if cls.fields:
            lines.append("| Field | Type | Description |")
            lines.append("| ----- | ---- | ----------- |")

            for name, type_hint, desc in cls.fields:
                # Linkify types in the type column (no backticks so links work)
                linked_type = self.linkify_type(type_hint)
                desc_str = self.escape_mdx_braces(desc) if desc else "-"
                lines.append(f"| {name} | {linked_type} | {desc_str} |")

            lines.append("")

        return "\n".join(lines)

    def generate_type_reference_section(self, classes: list[ParsedClass]) -> str:
        """Generate the Types Reference section."""
        lines = []

        lines.append("---")
        lines.append("")
        lines.append("## Types Reference")
        lines.append("")
        lines.append("This section documents the TypedDict and dataclass types used throughout the SDK.")
        lines.append("")

        typeddict_classes = [c for c in classes if c.name in self.export_typeddicts]

        # Separate entity classes from other response types
        entity_class_names = {c.name for c in classes if c.name.startswith("Entity") or c.name in ["CompanyEntity", "PersonEntity"]}
        result_classes = [c for c in classes if c.name not in self.export_typeddicts and c.name not in entity_class_names]
        entity_classes = [c for c in classes if c.name in entity_class_names]

        if typeddict_classes:
            lines.append("### Content Options")
            lines.append("")
            lines.append("These TypedDict classes configure content retrieval options for the `contents` parameter.")
            lines.append("")

            for cls in typeddict_classes:
                lines.append(self.generate_class_markdown(cls))

        if result_classes:
            lines.append("### Response Types")
            lines.append("")
            lines.append("These dataclasses represent API response objects.")
            lines.append("")

            for cls in result_classes:
                lines.append(self.generate_class_markdown(cls))

        # Entity types section
        if entity_classes or self.manual_types:
            lines.append("### Entity Types")
            lines.append("")
            lines.append("These types represent structured entity data returned for company or person searches.")
            lines.append("")

            # Add manual types first (like Entity union)
            for type_name, type_info in self.manual_types.items():
                lines.append(f"#### `{type_name}`")
                lines.append("")
                # Linkify types in description and definition
                desc = self.linkify_type(type_info["description"])
                definition = self.linkify_type(type_info["definition"])
                lines.append(desc)
                lines.append("")
                lines.append(f"**Type:** {definition}")
                lines.append("")

            # Add entity classes
            for cls in entity_classes:
                lines.append(self.generate_class_markdown(cls))

        return "\n".join(lines)

    def generate_full_documentation(self, api_filepath: Path, research_filepath: Path, research_models_filepath: Path) -> str:
        """Generate the full markdown documentation."""
        methods_by_class, classes = self.parse_sdk_file(api_filepath)
        research_methods, _ = self.parse_sdk_file(research_filepath, self.export_research_methods)
        # Parse research models for Pydantic DTOs
        _, research_classes = self.parse_sdk_file(research_models_filepath)
        classes.extend(research_classes)

        # Store parsed classes for lookup by generate_method_markdown
        for cls in classes:
            self.parsed_classes[cls.name] = cls

        lines = []

        # Frontmatter
        lines.append("---")
        lines.append('title: "Python SDK Specification"')
        lines.append('description: "Enumeration of methods and types in the Exa Python SDK (exa_py)."')
        lines.append("---")
        lines.append("")

        # Getting Started section
        lines.append(self.generate_getting_started_section())

        # Exa class methods
        if "Exa" in methods_by_class:
            for method in methods_by_class["Exa"]:
                lines.append(self.generate_method_markdown(method, "Exa"))

        # Research client methods
        if "ResearchClient" in research_methods:
            for method in research_methods["ResearchClient"]:
                lines.append(self.generate_method_markdown(method, "ResearchClient"))

        # Types Reference section
        if classes:
            lines.append(self.generate_type_reference_section(classes))

        return "\n".join(lines)


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    config_file = script_dir / "gen_config.json"
    api_file = script_dir.parent / "exa_py" / "api.py"
    research_file = script_dir.parent / "exa_py" / "research" / "sync_client.py"
    research_models_file = script_dir.parent / "exa_py" / "research" / "models.py"

    if not config_file.exists():
        print(f"Error: Config file not found at {config_file}", file=sys.stderr)
        sys.exit(1)

    if not api_file.exists():
        print(f"Error: API file not found at {api_file}", file=sys.stderr)
        sys.exit(1)

    if not research_file.exists():
        print(f"Error: Research client file not found at {research_file}", file=sys.stderr)
        sys.exit(1)

    if not research_models_file.exists():
        print(f"Error: Research models file not found at {research_models_file}", file=sys.stderr)
        sys.exit(1)

    generator = DocGenerator(config_file)
    docs = generator.generate_full_documentation(api_file, research_file, research_models_file)
    print(docs)


if __name__ == "__main__":
    main()
