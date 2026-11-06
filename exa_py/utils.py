import importlib.metadata
import json
from typing import TYPE_CHECKING, Any, Optional, Union
from openai.types.chat import ChatCompletion

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema

if TYPE_CHECKING:
    from exa_py.api import ResultWithText, SearchResponse


def maybe_get_query(completion) -> Optional[str]:
    """Extract query from completion if it exists."""
    if completion.choices[0].message.tool_calls:
        for tool_call in completion.choices[0].message.tool_calls:
            if tool_call.function.name == "search":
                query = json.loads(tool_call.function.arguments)["query"]
                return query
    return None


def add_message_to_messages(completion, messages, exa_result) -> list[dict]:
    """Add assistant message and exa result to messages list. Also remove previous exa call and results."""
    assistant_message = completion.choices[0].message
    assert assistant_message.tool_calls, "Must use this with a tool call request"
    # Remove previous exa call and results to prevent blowing up history
    messages = [
        message for message in messages if not (message.get("role") == "function")
    ]

    messages.extend(
        [
            assistant_message,
            {
                "role": "tool",
                "name": "search",
                "tool_call_id": assistant_message.tool_calls[0].id,
                "content": exa_result,
            },
        ]
    )

    return messages


def format_exa_result(exa_result, max_len: int = -1):
    """Format exa result for pasting into chat."""
    str = [
        f"Url: {result.url}\nTitle: {result.title}\n{result.text[:max_len]}\n"
        for result in exa_result.results
    ]

    return "\n".join(str)


class ExaOpenAICompletion(ChatCompletion):
    """Exa wrapper for OpenAI completion."""

    def __init__(
        self,
        exa_result: Optional["SearchResponse[ResultWithText]"],
        id,
        choices,
        created,
        model,
        object,
        system_fingerprint=None,
        usage=None,
    ):
        super().__init__(
            id=id,
            choices=choices,
            created=created,
            model=model,
            object=object,
            system_fingerprint=system_fingerprint,
            usage=usage,
        )
        self.exa_result = exa_result

    @classmethod
    def from_completion(
        cls,
        exa_result: Optional["SearchResponse[ResultWithText]"],
        completion: ChatCompletion,
    ):
        return cls(
            exa_result=exa_result,
            id=completion.id,
            choices=completion.choices,
            created=completion.created,
            model=completion.model,
            object=completion.object,
            system_fingerprint=completion.system_fingerprint,
            usage=completion.usage,
        )


JSONSchemaInput = Union[type[BaseModel], dict[str, Any]]

# Keywords that describe a schema without constraining what it accepts.
_ANNOTATION_KEYWORDS = frozenset(
    {"title", "description", "examples", "default", "deprecated", "readOnly", "writeOnly", "$comment"}
)


class InlineJsonSchemaGenerator(GenerateJsonSchema):
    """Custom JSON schema generator that inlines all schemas without creating $defs references."""

    def generate(self, schema, mode="validation"):
        """Generate JSON schema normally, then post-process to inline all refs."""
        # Let Pydantic do its normal thing first
        result = super().generate(schema, mode)

        # Post-process to inline all $ref references
        if "$defs" in result:
            definitions = result["$defs"]
            inlined_result = self._inline_refs(result, definitions)
            # Remove $defs since everything is now inlined
            if "$defs" in inlined_result:
                del inlined_result["$defs"]
            return inlined_result

        return result

    def _inline_refs(self, obj, definitions):
        """Recursively replace every resolvable ``#/$defs/`` reference with its definition.

        A ``$ref`` with sibling keywords applies the definition in place beside the
        siblings. When every sibling is an annotation (a field's description or
        title), they are merged into the definition and win over its own. Otherwise
        the siblings stay where they were and the definition moves into their
        ``allOf``, which applies it in place exactly as the ``$ref`` did, so a
        keyword that depends on what its neighbours evaluated
        (``unevaluatedProperties``) or one the definition also sets (``required``)
        keeps its meaning. A reference that cannot be resolved is kept, and its
        siblings are still inlined.
        """
        if isinstance(obj, dict):
            definition = self._ref_definition(obj, definitions)
            siblings = {
                key: self._inline_refs(value, definitions)
                for key, value in obj.items()
                if definition is None or key != "$ref"
            }
            if definition is None:
                return siblings
            resolved = self._inline_refs(definition, definitions)
            if siblings.keys() <= _ANNOTATION_KEYWORDS:
                return {**resolved, **siblings}
            return {**siblings, "allOf": [resolved, *siblings.get("allOf", [])]}
        elif isinstance(obj, list):
            # Process all items in the list
            return [self._inline_refs(item, definitions) for item in obj]
        else:
            # Primitive value, return as-is
            return obj

    @staticmethod
    def _ref_definition(obj, definitions):
        """The definition ``obj["$ref"]`` points at in ``definitions``, or None."""
        ref_path = obj.get("$ref")
        if not isinstance(ref_path, str) or not ref_path.startswith("#/$defs/"):
            return None
        return definitions.get(ref_path[len("#/$defs/"):])


def _convert_schema_input(schema_input: "JSONSchemaInput") -> dict[str, Any]:
    """Convert various schema input types to JSON Schema dict.

    Args:
        schema_input: Either a Pydantic BaseModel class or a dict containing JSON Schema

    Returns:
        dict: JSON Schema representation (fully inlined without $defs)
    """
    # Check if it's a Pydantic model class (not instance)
    if isinstance(schema_input, type) and issubclass(schema_input, BaseModel):
        return schema_input.model_json_schema(
            by_alias=False,
            mode="serialization",
            schema_generator=InlineJsonSchemaGenerator,
        )
    elif isinstance(schema_input, dict):
        return schema_input
    else:
        raise ValueError(
            f"Unsupported schema type: {type(schema_input)}. Expected BaseModel class or dict."
        )


def _get_package_version() -> str:
    """Return the version of exa-py, or "unknown" when it cannot be found.

    An installed package reports the version in its distribution metadata. A
    source checkout that is imported without being installed has no metadata,
    so the version comes from the pyproject.toml beside the package instead.
    """
    try:
        return importlib.metadata.version("exa-py")
    except importlib.metadata.PackageNotFoundError:
        pass

    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # fallback for older versions

        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        pyproject_path = os.path.join(project_root, "pyproject.toml")

        if os.path.exists(pyproject_path):
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "unknown")
    except Exception:
        pass

    return "unknown"
