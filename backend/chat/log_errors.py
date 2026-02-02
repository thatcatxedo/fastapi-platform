"""
Error parsing module for extracting structured errors from app logs.
Used by get_app_logs and diagnose_app tools.
"""

import re
from typing import Optional

# Error patterns: (regex, error_type, suggestion_template)
# Template uses {0}, {1}, etc. for regex group substitution
ERROR_PATTERNS = [
    # Import errors
    (r"ImportError.*No module named ['\"]?(\w+)['\"]?", "import_error",
     "Module '{0}' is not in allowed imports. Check platform docs for available modules."),
    (r"ModuleNotFoundError.*No module named ['\"]?(\w+)['\"]?", "import_error",
     "Module '{0}' not available. Use allowed imports only."),

    # Syntax errors
    (r"SyntaxError: (.+)", "syntax_error", "Syntax error: {0}"),
    (r"IndentationError: (.+)", "syntax_error", "Indentation error: {0}. Check for mixed tabs/spaces."),

    # Name/reference errors
    (r"NameError.*name ['\"](\w+)['\"] is not defined", "name_error",
     "Variable '{0}' used before definition. Check spelling or add import."),
    (r"UnboundLocalError.*['\"](\w+)['\"]", "name_error",
     "Variable '{0}' referenced before assignment in function."),

    # Key/attribute errors
    (r"KeyError.*['\"](\w+)['\"]", "key_error",
     "Key '{0}' not found. Check dict keys or use .get() with default."),
    (r"AttributeError.*['\"](\w+)['\"].*has no attribute ['\"](\w+)['\"]", "attr_error",
     "'{0}' has no attribute '{1}'. Check object type or spelling."),

    # Type errors
    (r"TypeError.*(\d+) positional argument", "type_error",
     "Wrong number of arguments ({0} given). Check function signature."),
    (r"TypeError.*got an unexpected keyword argument ['\"](\w+)['\"]", "type_error",
     "Unexpected keyword argument '{0}'. Check function parameters."),
    (r"TypeError.*'(\w+)' object is not (callable|iterable|subscriptable)", "type_error",
     "'{0}' is not {1}. Check variable type."),

    # Value errors
    (r"ValueError: (.+)", "value_error", "Invalid value: {0}"),

    # Connection errors
    (r"Connection refused", "connection_error",
     "Connection refused. Check database URI or service availability."),
    (r"ServerSelectionTimeoutError", "connection_error",
     "MongoDB connection timeout. Verify PLATFORM_MONGO_URI is correct."),
    (r"PLATFORM_MONGO_URI", "config_hint",
     "Use os.environ.get('PLATFORM_MONGO_URI') to get database connection string."),

    # App startup errors
    (r"Error: Code must define an app instance", "startup_error",
     "Missing 'app' variable. Define app = FastAPI() or app, rt = fast_app()."),
    (r"Error: Code file not found", "startup_error",
     "Entry file not found. Ensure app.py exists for multi-file apps."),
    (r"Error executing user code: (.+)", "execution_error",
     "Code execution failed: {0}"),

    # HTTP/request errors
    (r"422 Unprocessable Entity", "validation_error",
     "Request validation failed. Check request body/params match endpoint schema."),
    (r"500 Internal Server Error", "server_error",
     "Internal server error. Check logs for traceback."),
]


def parse_errors(log_lines: list[str]) -> dict:
    """
    Parse log lines and extract structured errors with suggestions.

    Args:
        log_lines: List of log message strings

    Returns:
        dict with:
            - errors_detected: List of structured error objects
            - has_errors: Boolean indicating if errors found
            - error_summary: One-line summary string
            - traceback: Extracted traceback if found
    """
    log_text = "\n".join(log_lines)
    errors_detected = []
    seen_types = set()

    for i, line in enumerate(log_lines):
        for pattern, error_type, suggestion_template in ERROR_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                # Build suggestion with captured groups
                try:
                    suggestion = suggestion_template.format(*match.groups()) if suggestion_template else None
                except (IndexError, KeyError):
                    suggestion = suggestion_template

                # Extract the actual error message
                error_msg = match.group(0)

                # Avoid duplicate errors of same type with same message
                error_key = (error_type, error_msg)
                if error_key not in seen_types:
                    seen_types.add(error_key)
                    errors_detected.append({
                        "type": error_type,
                        "message": error_msg,
                        "line_index": i,
                        "suggestion": suggestion
                    })
                break  # One pattern match per line

    # Extract traceback if present
    traceback = extract_traceback(log_lines)

    # Build summary
    if not errors_detected:
        error_summary = "No errors detected in logs"
    elif len(errors_detected) == 1:
        error_summary = f"1 {errors_detected[0]['type'].replace('_', ' ')} detected"
    else:
        type_counts = {}
        for e in errors_detected:
            t = e['type'].replace('_', ' ')
            type_counts[t] = type_counts.get(t, 0) + 1
        parts = [f"{count} {t}" for t, count in type_counts.items()]
        error_summary = f"{len(errors_detected)} errors: {', '.join(parts)}"

    return {
        "errors_detected": errors_detected,
        "has_errors": len(errors_detected) > 0,
        "error_summary": error_summary,
        "traceback": traceback
    }


def extract_traceback(log_lines: list[str]) -> Optional[str]:
    """
    Extract Python traceback from log lines.

    Returns the traceback as a string, or None if not found.
    """
    traceback_lines = []
    in_traceback = False

    for line in log_lines:
        if "Traceback (most recent call last)" in line:
            in_traceback = True
            traceback_lines = [line]
        elif in_traceback:
            traceback_lines.append(line)
            # End traceback at the exception line (not indented, contains Error/Exception)
            if line and not line.startswith(" ") and ("Error" in line or "Exception" in line):
                break

    if traceback_lines:
        return "\n".join(traceback_lines)
    return None


def get_error_suggestion(error_type: str, match_groups: tuple = ()) -> str:
    """
    Get a suggestion for a specific error type.
    Used by diagnose_app for compatibility.
    """
    for pattern, etype, suggestion in ERROR_PATTERNS:
        if etype == error_type and suggestion:
            try:
                return suggestion.format(*match_groups)
            except (IndexError, KeyError):
                return suggestion
    return ""
