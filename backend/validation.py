"""
Code validation module for FastAPI Platform
Validates user-submitted Python code for syntax and security
"""
import ast
import re
from typing import Optional, Dict, Tuple, Iterable, Set

ALLOWED_IMPORTS = {
    'fastapi', 'pydantic', 'typing', 'datetime', 'json', 'math',
    'random', 'string', 'collections', 'itertools', 'functools',
    'operator', 're', 'uuid', 'hashlib', 'base64', 'urllib', 'urllib.parse',
    'fasthtml', 'fastlite', 'os', 'sys', 'pathlib', 'time', 'enum',
    'dataclasses', 'decimal', 'html', 'http', 'copy', 'textwrap',
    'calendar', 'locale', 'secrets', 'statistics',
    'pymongo', 'bson', 'jinja2',
    'httpx', 'slack_sdk', 'google.auth', 'googleapiclient'
}

# Forbidden patterns - dangerous operations that should never be allowed
# Note: Import restrictions are handled separately via ALLOWED_IMPORTS
FORBIDDEN_PATTERNS = [
    r'__import__',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bcompile\s*\(',
    r'\bopen\s*\(',
    r'\bfile\s*\(',
    r'\bsubprocess\b',
    r'os\.system',
    r'os\.popen',
]


def find_forbidden_calls(tree: ast.AST, names: set) -> Optional[tuple[str, int]]:
    """Return (name, line) for forbidden call names found in AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in names:
                return node.func.id, node.lineno
    return None


def _normalize_allowed_imports(
    allowed_imports_override: Optional[Iterable[str]]
) -> Optional[Set[str]]:
    if allowed_imports_override is None:
        return None
    normalized = {
        item.strip().lower()
        for item in allowed_imports_override
        if isinstance(item, str) and item.strip()
    }
    return normalized or None


def validate_code(
    code: str,
    local_modules: Optional[set] = None,
    allowed_imports_override: Optional[Iterable[str]] = None
) -> tuple[bool, Optional[str], Optional[int]]:
    """Validate user code for syntax and security.
    Returns (is_valid, error_message, line_number)

    Args:
        code: The Python code to validate
        local_modules: Set of module names that are local to this multi-file app
                      (e.g., {'routes', 'models'} for files routes.py, models.py)
    """
    if local_modules is None:
        local_modules = set()
    # Check for empty code
    if not code or not code.strip():
        return False, "Code cannot be empty. Please write some Python code.", None
    
    # Basic syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        # Provide more helpful syntax error messages
        error_msg = e.msg
        if "invalid syntax" in error_msg.lower():
            if "expected" in error_msg.lower():
                error_msg = f"Syntax error: {e.msg}. Check for missing colons, parentheses, or brackets."
            else:
                error_msg = f"Syntax error: {e.msg}. Check line {e.lineno} for typos or missing characters."
        else:
            error_msg = f"Syntax error: {e.msg}"
        return False, error_msg, e.lineno

    # Check that an app is created (FastAPI or FastHTML)
    has_fastapi_app = False
    has_fasthtml_app = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            func_name = func.id if isinstance(func, ast.Name) else None
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'app':
                    if func_name == 'FastAPI':
                        has_fastapi_app = True
                    if func_name in ('fast_app', 'FastHTML'):
                        has_fasthtml_app = True
                elif isinstance(target, ast.Tuple) and func_name in ('fast_app', 'FastHTML'):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name) and elt.id == 'app':
                            has_fasthtml_app = True

    if not (has_fastapi_app or has_fasthtml_app):
        return False, "Your code must create an app instance. Add: app = FastAPI() (or app, rt = fast_app() for FastHTML)", None

    # Security checks - check imports
    # Combine allowed imports with local modules for multi-file apps
    base_allowed = _normalize_allowed_imports(allowed_imports_override) or ALLOWED_IMPORTS
    allowed = base_allowed | local_modules

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name not in allowed:
                    # Provide helpful suggestions for common imports
                    suggestions = []
                    if 'requests' in module_name.lower():
                        suggestions.append("Use urllib.parse for URL handling instead")
                    elif 'pandas' in module_name.lower() or 'numpy' in module_name.lower():
                        suggestions.append("Data processing libraries are not available. Use built-in Python types.")
                    elif 'flask' in module_name.lower() or 'django' in module_name.lower():
                        suggestions.append("This platform uses FastAPI. Import from 'fastapi' instead.")

                    suggestion_text = f" {suggestions[0]}" if suggestions else ""
                    return False, f"Import '{module_name}' is not allowed.{suggestion_text} Allowed imports: {', '.join(sorted(base_allowed))}", node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name not in allowed:
                    suggestions = []
                    if 'requests' in module_name.lower():
                        suggestions.append("Use urllib.parse for URL handling instead")
                    elif 'pandas' in module_name.lower() or 'numpy' in module_name.lower():
                        suggestions.append("Data processing libraries are not available. Use built-in Python types.")
                    elif 'flask' in module_name.lower() or 'django' in module_name.lower():
                        suggestions.append("This platform uses FastAPI. Import from 'fastapi' instead.")

                    suggestion_text = f" {suggestions[0]}" if suggestions else ""
                    return False, f"Import '{module_name}' is not allowed.{suggestion_text} Allowed imports: {', '.join(sorted(base_allowed))}", node.lineno

    # Check for forbidden call names (case-sensitive to avoid FastHTML Input)
    forbidden_call = find_forbidden_calls(tree, {"input", "raw_input"})
    if forbidden_call:
        name, line_num = forbidden_call
        message = "input() is not allowed. Use FastAPI request parameters instead."
        if name == "raw_input":
            message = "raw_input() is not allowed. Use FastAPI request parameters instead."
        return False, message, line_num

    # Check for forbidden patterns with better error messages
    # Use \b word boundary to avoid false positives (e.g., urlopen matching open)
    # Note: Import-based restrictions are handled by allowed_imports, not here
    forbidden_patterns_map = {
        r'__import__': "Direct use of __import__() is not allowed for security reasons.",
        r'\beval\s*\(': "eval() is not allowed for security reasons. Use proper code structure instead.",
        r'\bexec\s*\(': "exec() is not allowed for security reasons. Use proper code structure instead.",
        r'\bcompile\s*\(': "compile() is not allowed for security reasons.",
        r'\bopen\s*\(': "File operations are not allowed. Use environment variables or in-memory data instead.",
        r'\bfile\s*\(': "File operations are not allowed. Use environment variables or in-memory data instead.",
        r'\bsubprocess\b': "subprocess is not allowed for security reasons.",
        r'os\.system': "os.system() is not allowed for security reasons.",
        r'os\.popen': "os.popen() is not allowed for security reasons.",
    }
    
    for pattern, friendly_msg in forbidden_patterns_map.items():
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            # Find line number of the match
            line_num = code[:match.start()].count('\n') + 1
            return False, friendly_msg, line_num

    return True, None, None


def validate_code_syntax_only(
    code: str,
    local_modules: Optional[set] = None,
    allowed_imports_override: Optional[Iterable[str]] = None
) -> tuple[bool, Optional[str], Optional[int]]:
    """Validate code syntax and security without requiring app definition.
    Used for non-entrypoint files in multi-file mode.
    Returns (is_valid, error_message, line_number)

    Args:
        code: The Python code to validate
        local_modules: Set of module names that are local to this multi-file app
    """
    if local_modules is None:
        local_modules = set()

    # Check for empty code
    if not code or not code.strip():
        return False, "Code cannot be empty.", None

    # Basic syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        error_msg = e.msg
        if "invalid syntax" in error_msg.lower():
            if "expected" in error_msg.lower():
                error_msg = f"Syntax error: {e.msg}. Check for missing colons, parentheses, or brackets."
            else:
                error_msg = f"Syntax error: {e.msg}. Check line {e.lineno} for typos or missing characters."
        else:
            error_msg = f"Syntax error: {e.msg}"
        return False, error_msg, e.lineno

    # Security checks - check imports
    # Combine allowed imports with local modules for multi-file apps
    base_allowed = _normalize_allowed_imports(allowed_imports_override) or ALLOWED_IMPORTS
    allowed = base_allowed | local_modules

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name not in allowed:
                    return False, f"Import '{module_name}' is not allowed. Allowed imports: {', '.join(sorted(base_allowed))}", node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name not in allowed:
                    return False, f"Import '{module_name}' is not allowed. Allowed imports: {', '.join(sorted(base_allowed))}", node.lineno

    # Check for forbidden call names (case-sensitive to avoid FastHTML Input)
    forbidden_call = find_forbidden_calls(tree, {"input", "raw_input"})
    if forbidden_call:
        name, line_num = forbidden_call
        message = "input() is not allowed."
        if name == "raw_input":
            message = "raw_input() is not allowed."
        return False, message, line_num

    # Check for forbidden patterns
    # Use \b word boundary to avoid false positives (e.g., urlopen matching open)
    # Note: Import-based restrictions are handled by allowed_imports, not here
    forbidden_patterns_map = {
        r'__import__': "Direct use of __import__() is not allowed for security reasons.",
        r'\beval\s*\(': "eval() is not allowed for security reasons.",
        r'\bexec\s*\(': "exec() is not allowed for security reasons.",
        r'\bcompile\s*\(': "compile() is not allowed for security reasons.",
        r'\bopen\s*\(': "File operations are not allowed.",
        r'\bfile\s*\(': "File operations are not allowed.",
        r'\bsubprocess\b': "subprocess is not allowed for security reasons.",
        r'os\.system': "os.system() is not allowed for security reasons.",
        r'os\.popen': "os.popen() is not allowed for security reasons.",
    }

    for pattern, friendly_msg in forbidden_patterns_map.items():
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            line_num = code[:match.start()].count('\n') + 1
            return False, friendly_msg, line_num

    return True, None, None


def validate_multifile(
    files: Dict[str, str],
    entrypoint: str = "app.py",
    allowed_imports_override: Optional[Iterable[str]] = None
) -> Tuple[bool, str, Optional[int], Optional[str]]:
    """
    Validate all files in a multi-file app.
    Returns: (is_valid, error_message, error_line, error_file)
    """
    # Guardrails
    MAX_FILES = 10
    MAX_FILE_SIZE = 100 * 1024  # 100KB per file
    MAX_TOTAL_SIZE = 500 * 1024  # 500KB total

    if not files:
        return False, "No files provided", None, None

    if len(files) > MAX_FILES:
        return False, f"Too many files (max {MAX_FILES})", None, None

    total_size = sum(len(content) for content in files.values())
    if total_size > MAX_TOTAL_SIZE:
        return False, f"Total size exceeds {MAX_TOTAL_SIZE // 1024}KB", None, None

    if entrypoint not in files:
        return False, f"Entrypoint '{entrypoint}' not found in files", None, None

    # Build set of local module names (file names without .py extension)
    # This allows imports between files in the same multi-file app
    local_modules = {
        filename[:-3]  # Remove .py extension
        for filename in files.keys()
        if filename.endswith('.py')
    }

    # Validate each file
    for filename, content in files.items():
        if not filename.endswith('.py'):
            return False, f"Only .py files allowed: {filename}", None, filename

        if len(content) > MAX_FILE_SIZE:
            return False, f"File too large: {filename} (max {MAX_FILE_SIZE // 1024}KB)", None, filename

        if filename == entrypoint:
            # Entrypoint must define an app
            is_valid, error_msg, error_line = validate_code(
                content,
                local_modules,
                allowed_imports_override
            )
        else:
            # Other files: syntax and security only, no app required
            is_valid, error_msg, error_line = validate_code_syntax_only(
                content,
                local_modules,
                allowed_imports_override
            )

        if not is_valid:
            return False, error_msg, error_line, filename

    return True, "", None, None
