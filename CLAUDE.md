# Claude Code Guidelines for exa-py

## SDK Documentation Auto-Generation

This SDK uses auto-generated documentation from code. When making modifications, ensure the documentation stays up to date:

### Docstrings
- All public methods should have Google-style docstrings with `Args`, `Returns`, and `Examples` sections
- Examples in docstrings are extracted and displayed in the generated docs
- Parameter descriptions in `Args` sections become the "Description" column in parameter tables

### Type Hints
- All parameters and return types should have proper type hints
- Types referenced in hints are automatically linked in the documentation
- For Pydantic models, use `Field(description="...")` to document fields

### Adding New Types
- New classes in `api.py` or `research/models.py` are auto-discovered and documented
- Private classes (starting with `_`) are excluded unless explicitly listed in `scripts/gen_config.json`
- Type aliases (like `Union[...]`) that can't be classes must be added to `manual_types` in the config

### Generating Documentation
Run the documentation generator to verify changes:
```bash
python scripts/generate_docs.py > docs/python-sdk-specification.mdx
```

### Config File
See `scripts/gen_config.json` for:
- `output_examples` - JSON response examples for each method
- `method_result_objects` - Maps methods to their result object types
- `manual_types` - Type aliases that need manual documentation
- `external_type_links` - Links to external documentation (e.g., Pydantic's BaseModel)
