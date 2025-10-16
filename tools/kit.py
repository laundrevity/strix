from pathlib import Path
import importlib.util
import inspect


_PYTHON_TO_JSON_TYPE = {
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "str": "string",
}


def tool(description, **arg_descriptions):
    def inner(func):
        schema = {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,  # Add this for stricter validation
                },
            },
        }

        # Get function signature
        sig = inspect.signature(func)

        # Process parameters
        for param_name, param in sig.parameters.items():
            # Skip self parameter for methods
            if param_name == "self":
                continue

            # Create parameter schema
            param_type = _PYTHON_TO_JSON_TYPE.get(param.annotation.__name__, "string")
            param_schema = {
                "type": param_type,
                "description": arg_descriptions.get(
                    param_name, f"Parameter {param_name}"
                ),
            }

            # Check if parameter has default value (optional)
            if param.default is not inspect.Parameter.empty:
                # This parameter is optional, don't add to required
                param_schema["default"] = param.default
            else:
                # This parameter is required
                schema["function"]["parameters"]["required"].append(param_name)

            schema["function"]["parameters"]["properties"][param_name] = param_schema

        func.schema = schema
        return func

    return inner


def gather_tools(ref):
    schemas = []
    tools = {}
    current_file, current_dir = Path(__file__).name, Path(__file__).parent

    for py_file in current_dir.glob("*.py"):
        if py_file.name == current_file:
            continue

        module_name = "tools." + py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # find (coro) functions with a .schema attribute
        for name, obj in vars(module).items():
            if (
                inspect.isfunction(obj) or inspect.iscoroutinefunction(obj)
            ) and hasattr(obj, "schema"):
                schemas.append(obj.schema)
                tools[name] = obj
                setattr(obj, "ref", ref)

    return schemas, tools
