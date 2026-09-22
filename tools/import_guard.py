#!/usr/bin/env python3
"""Clean-room import guard.

Fails the build if shipped source references a forbidden external codebase or
absolute path. This enforces the frozen constraint that council-mcp is fully
independent: no KAAAJ / Brain OS imports, no paths into another project's tree.

Detection:
  * AST scan for `import <mod>` / `from <mod> import ...` where the top-level
    module is in FORBIDDEN_MODULES.
  * Text scan for FORBIDDEN_PATH_SUBSTRINGS anywhere in the file.

Usage:
  python tools/import_guard.py [path ...]     # default: src/ and tools/
  exit code 0 = clean, 1 = violations found (printed to stderr).

The guard scans production/shipped code (src/, tools/). Test files may legally
contain the forbidden strings as fixtures, so they are not scanned by default;
tests exercise this module's functions with synthetic input instead.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

# Built from a fragment so this guard file does not itself contain the literal
# forbidden path (which would otherwise trip the guard when it scans tools/).
_FORBIDDEN_DIR = "k" + "aaaj"
FORBIDDEN_MODULES = frozenset({_FORBIDDEN_DIR, "brainos", "genie"})
FORBIDDEN_PATH_SUBSTRINGS = (
    f"/home/{_FORBIDDEN_DIR}/{_FORBIDDEN_DIR}",
    f"~/{_FORBIDDEN_DIR}",
)


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.kind}: {self.detail}"


def scan_text(text: str, name: str = "<text>") -> list[Violation]:
    """Scan a single source string; return all violations found."""
    violations: list[Violation] = []

    # 1) Path-substring text scan (line-numbered).
    for lineno, line in enumerate(text.splitlines(), start=1):
        for needle in FORBIDDEN_PATH_SUBSTRINGS:
            if needle in line:
                violations.append(Violation(name, lineno, "forbidden-path", needle))

    # 2) AST import scan (best-effort; syntax errors are reported, not swallowed).
    try:
        tree = ast.parse(text, filename=name)
    except SyntaxError as exc:  # pragma: no cover - defensive
        violations.append(Violation(name, exc.lineno or 0, "syntax-error", str(exc)))
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FORBIDDEN_MODULES:
                    violations.append(
                        Violation(name, node.lineno, "forbidden-import", alias.name)
                    )
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top in FORBIDDEN_MODULES:
                violations.append(
                    Violation(name, node.lineno, "forbidden-import", node.module or "")
                )
    return violations


def scan_paths(paths: list[Path]) -> list[Violation]:
    """Scan every *.py file under the given paths (files or directories)."""
    violations: list[Violation] = []
    for p in paths:
        files = [p] if p.is_file() else sorted(p.rglob("*.py"))
        for f in files:
            if f.suffix != ".py":
                continue
            violations.extend(scan_text(f.read_text(encoding="utf-8"), str(f)))
    return violations


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(__file__).resolve().parent.parent
    targets = [Path(a) for a in argv] if argv else [root / "src", root / "tools"]
    violations = scan_paths([t for t in targets if t.exists()])
    if violations:
        print("IMPORT GUARD FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("import guard: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
