from pathlib import Path

from tools.kit import tool


_ROOT_DIR = Path(__file__).parent.parent.resolve()


_DESCRIPTION = f"""Edit (or create) a file by **literal string replacement**.

    INSTRUCTIONS (read carefully - invalid parameters cause hard failure):
    • file_path must be ABSOLUTE and MUST reside inside the project root directory: {_ROOT_DIR}
    • To create a brand-new file: set old_string='' and put full file contents in new_string."
    • To modify an existing file: old_string must be the exact literal text to replace, including"
      all whitespace, indentation and newlines.  Provide enough context so it matches uniquely."
    • expected_replacements defaults to 1; if the actual replacement count differs, the tool fails."
    • Do not guess paths or counts - think step-by-step or `cat` the file first using shell tool, then call this tool 
    once with correct parameters."""


_PARAM_DOCS = dict(
    file_path="Absolute path of the target file (must be inside the project root shown above).",
    old_string="Exact literal text to replace.  Use '' only when creating a new file.",
    new_string="Exact literal text that will replace old_string (or full file content if creating).",
    expected_replacements="How many occurrences you expect to replace, defaults to 1. Use 1 if creating new file.",
)


@tool(_DESCRIPTION, **_PARAM_DOCS)
def replace(
    file_path: str, old_string: str, new_string: str, expected_replacements: int = 1
) -> str:
    try:
        root_dir = _ROOT_DIR
        path_obj = Path(file_path)

        # validate
        if not path_obj.is_absolute():
            return f"Error: file_path[{file_path}] must be absolute"
        try:
            path_obj.resolve().relative_to(root_dir)
        except ValueError:
            return f"Error: file_path[{file_path}] must be within project root[{_ROOT_DIR}]"
        if expected_replacements < 1:
            return f"Error: expected_replacements[{expected_replacements}] must be >= 1"

        file_exists = path_obj.exists()

        # create new file
        if old_string == "":
            if file_exists:
                return f"Error: Failed to edit. Attempted to create file[{file_path}] that already exists"
            path_obj.parent.mkdir(parent=True, exist_ok=True)
            path_obj.write_text(new_string, encoding="utf-8")
            return f"Created new file[{file_path}] with provided content"

        # exit existing file
        if not file_exists:
            return f"Error: file[{file_path}] not found. Cannot apply edit. Use an empty old_string to create a new file."

        current_content = path_obj.read_text(encoding="utf-8").replace("\r\n", "\n")
        occurrences = current_content.count(old_string)
        if occurrences == 0:
            return (
                "Error: Failed to edit, could not find the string to replace. "
                "Ensure old_string is exact (check whitespace & indentation)."
            )
        if occurrences != expected_replacements:
            term = "occurrence" if expected_replacements == 1 else "occurrences"
            return (
                f"Error: Failed to edit, expected {expected_replacements} {term} "
                f"but found {occurrences}."
            )

        new_content = current_content.replace(old_string, new_string)
        path_obj.write_text(new_content, encoding="utf-8")
        return f"Successfully modified file: {file_path} ({occurrences} replacements)."

    except Exception as exc:
        return f"Error executing edit: {exc}"
