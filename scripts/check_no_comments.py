import ast
import io
import json
import shutil
import subprocess
import sys
import tokenize
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

ESLINT_CHECKED_SUFFIXES = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts", ".cjs"})
SKIPPED_SUFFIXES = frozenset({".md", ".svg", ".ico", ".png", ".jpg", ".jpeg", ".woff2", ".pdf"})
SKIPPED_FILENAMES = frozenset({"uv.lock", "pnpm-lock.yaml", ".python-version"})
HASH_COMMENT_SUFFIXES = frozenset({".yml", ".yaml", ".toml", ".ini", ".cfg", ".sh", ".conf"})
HASH_COMMENT_FILENAMES = frozenset(
    {
        ".gitignore",
        ".dockerignore",
        ".gitattributes",
        ".prettierignore",
        ".env.example",
    }
)
EDITORCONFIG_FILENAME = ".editorconfig"
DOCKERFILE_NAME = "Dockerfile"
QUOTE_CHARACTERS = frozenset({'"', "'"})


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    reason: str


Checker = Callable[[Path, str], Iterator[Violation]]


def check_python(path: Path, source: str) -> Iterator[Violation]:
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            yield Violation(path, token.start[0], "Python comment")
    documented_nodes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, documented_nodes) and ast.get_docstring(node, clean=False):
            yield Violation(path, node.body[0].lineno, "docstring")


def find_unquoted_marker(line: str, marker: str) -> int:
    active_quote: str | None = None
    for index, character in enumerate(line):
        if active_quote:
            if character == active_quote:
                active_quote = None
            continue
        if character in QUOTE_CHARACTERS:
            active_quote = character
            continue
        is_marker = line.startswith(marker, index)
        if is_marker and (index == 0 or line[index - 1].isspace()):
            return index
    return -1


def check_hash_comments(path: Path, source: str) -> Iterator[Violation]:
    for number, line in enumerate(source.splitlines(), start=1):
        if find_unquoted_marker(line, "#") >= 0:
            yield Violation(path, number, "hash comment")


def check_dockerfile(path: Path, source: str) -> Iterator[Violation]:
    for number, line in enumerate(source.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            yield Violation(path, number, "Dockerfile comment")


def check_editorconfig(path: Path, source: str) -> Iterator[Violation]:
    for number, line in enumerate(source.splitlines(), start=1):
        if line.lstrip().startswith(("#", ";")):
            yield Violation(path, number, "editorconfig comment")


def check_strict_json(path: Path, source: str) -> Iterator[Violation]:
    try:
        json.loads(source)
    except json.JSONDecodeError as error:
        yield Violation(path, error.lineno, "not strict JSON, comments are not allowed")


def check_block_markers(*markers: str) -> Checker:
    def check(path: Path, source: str) -> Iterator[Violation]:
        for number, line in enumerate(source.splitlines(), start=1):
            for marker in markers:
                if find_unquoted_marker(line, marker) >= 0 or marker in line:
                    yield Violation(path, number, f"comment marker {marker!r}")

    return check


def check_mako(path: Path, source: str) -> Iterator[Violation]:
    for number, line in enumerate(source.splitlines(), start=1):
        if line.lstrip().startswith("##") or "<%doc>" in line:
            yield Violation(path, number, "Mako comment")


SUFFIX_CHECKERS: dict[str, Checker] = {
    ".py": check_python,
    ".json": check_strict_json,
    ".css": check_block_markers("/*"),
    ".html": check_block_markers("<!--", "{#"),
    ".txt": check_block_markers("{#"),
    ".sql": check_block_markers("--", "/*"),
    ".mako": check_mako,
}


def resolve_checker(path: Path) -> Checker | None:
    if path.suffix in ESLINT_CHECKED_SUFFIXES or path.suffix in SKIPPED_SUFFIXES:
        return None
    if path.name in SKIPPED_FILENAMES:
        return None
    if path.name == DOCKERFILE_NAME:
        return check_dockerfile
    if path.name == EDITORCONFIG_FILENAME:
        return check_editorconfig
    if path.name in HASH_COMMENT_FILENAMES or path.suffix in HASH_COMMENT_SUFFIXES:
        return check_hash_comments
    return SUFFIX_CHECKERS.get(path.suffix)


def list_repository_files() -> list[Path]:
    git_executable = shutil.which("git")
    if git_executable is None:
        message = "git executable not found in PATH"
        raise RuntimeError(message)
    output = subprocess.run(
        [git_executable, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return [REPOSITORY_ROOT / name for name in output.split("\0") if name]


def find_violations(paths: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in paths:
        checker = resolve_checker(path)
        if checker is None or not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        violations.extend(checker(path.relative_to(REPOSITORY_ROOT), source))
    return violations


def main() -> int:
    violations = find_violations(list_repository_files())
    for violation in violations:
        sys.stdout.write(f"{violation.path.as_posix()}:{violation.line}: {violation.reason}\n")
    if violations:
        sys.stdout.write(f"Found {len(violations)} comment(s). Comments are not allowed.\n")
        return 1
    sys.stdout.write("No comments found.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
