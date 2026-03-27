#!/usr/bin/env python3
"""
CodeScope — Python project analyzer
Usage: python codescope.py [path] [options]
"""

import ast
import argparse
import sys
import os
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.rule import Rule
    from rich.progress import track
    from rich import box
    import rich.style
except ImportError:
    print("Installing rich...")
    os.system(f"{sys.executable} -m pip install rich -q")
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.rule import Rule
    from rich.progress import track
    from rich import box

console = Console()

# ── Theme ──────────────────────────────────────────────────────────────────
C = {
    "accent":   "#64ffda",
    "accent2":  "#7b68ee",
    "dim":      "#4a4a6a",
    "warn":     "#ffb86c",
    "err":      "#ff5555",
    "ok":       "#50fa7b",
    "muted":    "#6272a4",
    "white":    "#f8f8f2",
    "heading":  "bold #64ffda",
}


# ── AST Analysis ───────────────────────────────────────────────────────────
class FileAnalysis:
    def __init__(self, path: Path):
        self.path = path
        self.lines = 0
        self.blank_lines = 0
        self.comment_lines = 0
        self.code_lines = 0
        self.functions = []
        self.classes = []
        self.imports = []
        self.todos = []
        self.complexity = 0
        self.errors = []

    @property
    def name(self):
        return self.path.name


def analyze_file(path: Path) -> FileAnalysis:
    fa = FileAnalysis(path)

    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        fa.errors.append(str(e))
        return fa

    lines = source.splitlines()
    fa.lines = len(lines)

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            fa.blank_lines += 1
        elif stripped.startswith("#"):
            fa.comment_lines += 1
            if any(tag in stripped.upper() for tag in ("TODO", "FIXME", "HACK", "XXX", "NOTE")):
                tag = next((t for t in ("TODO", "FIXME", "HACK", "XXX", "NOTE") if t in stripped.upper()), "TODO")
                fa.todos.append((i, tag, stripped.lstrip("#").strip()))
        else:
            fa.code_lines += 1

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        fa.errors.append(f"SyntaxError line {e.lineno}: {e.msg}")
        return fa

    for node in ast.walk(tree):
        # Functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_method = False
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    if node in ast.walk(parent):
                        is_method = True
            args = [a.arg for a in node.args.args]
            fa.functions.append({
                "name": node.name,
                "line": node.lineno,
                "args": args,
                "is_method": is_method,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "docstring": ast.get_docstring(node) or "",
            })

        # Classes
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(f"{base.value.id}.{base.attr}" if isinstance(base.value, ast.Name) else base.attr)
            fa.classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
                "bases": bases,
                "docstring": ast.get_docstring(node) or "",
            })

        # Imports
        elif isinstance(node, ast.Import):
            for alias in node.names:
                fa.imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                fa.imports.append(node.module.split(".")[0])

        # Cyclomatic complexity (rough: count branches)
        elif isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                               ast.With, ast.Assert, ast.comprehension)):
            fa.complexity += 1

    fa.complexity = max(1, fa.complexity)
    return fa


def scan_project(root: Path, ignore: list[str]) -> list[FileAnalysis]:
    ignore_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", "dist", "build", ".eggs"} | set(ignore)
    py_files = []
    for f in root.rglob("*.py"):
        if not any(part in ignore_dirs for part in f.parts):
            py_files.append(f)
    py_files.sort()

    results = []
    for f in track(py_files, description=f"[{C['accent']}]Scanning files...[/]", console=console):
        results.append(analyze_file(f))
    return results


# ── Report Sections ────────────────────────────────────────────────────────

def print_header(root: Path):
    console.print()
    title = Text()
    title.append("  CodeScope ", style=f"bold {C['accent']}")
    title.append("◈", style=f"bold {C['accent2']}")
    title.append("  Python Project Analyzer\n", style=f"dim {C['white']}")
    title.append(f"  {root.resolve()}", style=C["muted"])

    console.print(Panel(
        title,
        border_style=C["dim"],
        padding=(0, 1),
    ))
    console.print()


def print_summary(analyses: list[FileAnalysis], root: Path):
    total_files = len(analyses)
    total_lines = sum(a.lines for a in analyses)
    total_code = sum(a.code_lines for a in analyses)
    total_blank = sum(a.blank_lines for a in analyses)
    total_comments = sum(a.comment_lines for a in analyses)
    total_funcs = sum(len(a.functions) for a in analyses)
    total_classes = sum(len(a.classes) for a in analyses)
    total_todos = sum(len(a.todos) for a in analyses)
    total_errors = sum(len(a.errors) for a in analyses)
    avg_complexity = sum(a.complexity for a in analyses) / total_files if total_files else 0

    def stat(label, value, style=C["white"]):
        t = Text()
        t.append(f"  {str(value):>8}", style=f"bold {style}")
        t.append(f"  {label}\n", style=C["muted"])
        return t

    col1 = Text()
    col1.append(f"{'FILES':>8}  label\n", style="bold " + C["dim"])
    col1.append_text(stat("Python files", total_files, C["accent"]))
    col1.append_text(stat("Total lines", f"{total_lines:,}"))
    col1.append_text(stat("Code lines", f"{total_code:,}", C["ok"]))
    col1.append_text(stat("Comment lines", f"{total_comments:,}", C["muted"]))
    col1.append_text(stat("Blank lines", f"{total_blank:,}", C["dim"]))

    col2 = Text()
    col2.append(f"{'SYMBOLS':>8}  label\n", style="bold " + C["dim"])
    col2.append_text(stat("Functions", total_funcs, C["accent2"]))
    col2.append_text(stat("Classes", total_classes, C["accent2"]))
    col2.append_text(stat("TODOs / FIXMEs", total_todos, C["warn"]))
    col2.append_text(stat("Parse errors", total_errors, C["err"] if total_errors else C["ok"]))
    col2.append_text(stat("Avg complexity", f"{avg_complexity:.1f}", C["warn"] if avg_complexity > 10 else C["ok"]))

    console.print(Rule(f"[{C['heading']}]◈  PROJECT SUMMARY[/]", style=C["dim"]))
    console.print(Columns([
        Panel(col1, border_style=C["dim"], padding=(0, 1)),
        Panel(col2, border_style=C["dim"], padding=(0, 1)),
    ]))
    console.print()


def print_top_files(analyses: list[FileAnalysis], n=10):
    sorted_files = sorted(analyses, key=lambda a: a.lines, reverse=True)[:n]
    if not sorted_files:
        return

    table = Table(
        show_header=True,
        header_style=f"bold {C['accent']}",
        border_style=C["dim"],
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("File", style=C["white"], no_wrap=True, max_width=50)
    table.add_column("Lines", justify="right", style=C["accent"])
    table.add_column("Code", justify="right", style=C["ok"])
    table.add_column("Funcs", justify="right", style=C["accent2"])
    table.add_column("Classes", justify="right", style=C["accent2"])
    table.add_column("Complexity", justify="right")
    table.add_column("TODOs", justify="right", style=C["warn"])

    max_lines = sorted_files[0].lines if sorted_files else 1
    for a in sorted_files:
        bar_len = int((a.lines / max_lines) * 12)
        bar = f"[{C['dim']}]{'█' * bar_len}{'░' * (12 - bar_len)}[/]"
        cx = a.complexity
        cx_style = C["err"] if cx > 20 else (C["warn"] if cx > 10 else C["ok"])
        table.add_row(
            f"{bar} {a.path.name}",
            str(a.lines),
            str(a.code_lines),
            str(len(a.functions)),
            str(len(a.classes)),
            f"[{cx_style}]{cx}[/]",
            str(len(a.todos)) if a.todos else "[dim]-[/]",
        )

    console.print(Rule(f"[{C['heading']}]◈  TOP FILES BY SIZE[/]", style=C["dim"]))
    console.print(table)
    console.print()


def print_imports(analyses: list[FileAnalysis]):
    all_imports = []
    for a in analyses:
        all_imports.extend(a.imports)

    stdlib = {
        "os", "sys", "re", "io", "abc", "ast", "csv", "json", "math",
        "time", "uuid", "copy", "enum", "glob", "gzip", "hmac", "http",
        "html", "logging", "pathlib", "pickle", "random", "shutil",
        "socket", "sqlite3", "string", "struct", "textwrap", "threading",
        "traceback", "typing", "unittest", "urllib", "argparse", "collections",
        "contextlib", "dataclasses", "datetime", "functools", "hashlib",
        "importlib", "inspect", "itertools", "operator", "subprocess",
        "tempfile", "weakref", "zipfile", "configparser", "concurrent",
        "multiprocessing", "asyncio", "base64", "binascii", "codecs",
        "decimal", "difflib", "email", "ftplib", "getpass", "gettext",
        "heapq", "imaplib", "platform", "pprint", "profile", "queue",
        "readline", "shlex", "signal", "smtplib", "stat", "statistics",
        "tarfile", "telnetlib", "termios", "timeit", "token", "tokenize",
        "trace", "tty", "turtle", "types", "warnings", "xml", "xmlrpc",
        "builtins", "keyword", "linecache", "marshal", "mimetypes", "numbers",
    }

    counts = Counter(all_imports)
    third_party = {k: v for k, v in counts.items() if k not in stdlib and k}
    std_used = {k: v for k, v in counts.items() if k in stdlib}

    table = Table(
        show_header=True,
        header_style=f"bold {C['accent']}",
        border_style=C["dim"],
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("Package", style=C["white"])
    table.add_column("Used in", justify="right", style=C["accent"])
    table.add_column("Type", style=C["muted"])

    items = sorted(third_party.items(), key=lambda x: -x[1])[:15] + \
            sorted(std_used.items(), key=lambda x: -x[1])[:8]
    items = sorted(items, key=lambda x: -x[1])[:18]

    for pkg, count in items:
        pkg_type = "[dim]stdlib[/dim]" if pkg in stdlib else f"[{C['accent2']}]3rd-party[/]"
        table.add_row(pkg, str(count), pkg_type)

    console.print(Rule(f"[{C['heading']}]◈  TOP IMPORTS[/]", style=C["dim"]))
    console.print(table)
    console.print()


def print_todos(analyses: list[FileAnalysis]):
    all_todos = []
    for a in analyses:
        for lineno, tag, msg in a.todos:
            all_todos.append((a.path.name, lineno, tag, msg))

    if not all_todos:
        console.print(Rule(f"[{C['heading']}]◈  TODOS & FIXMES[/]", style=C["dim"]))
        console.print(f"  [{C['ok']}]✓ No TODOs found — clean codebase![/]\n")
        return

    table = Table(
        show_header=True,
        header_style=f"bold {C['accent']}",
        border_style=C["dim"],
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("File", style=C["muted"], no_wrap=True)
    table.add_column("Line", justify="right", style=C["dim"])
    table.add_column("Tag", style=C["warn"], no_wrap=True)
    table.add_column("Message", style=C["white"])

    TAG_STYLE = {
        "TODO": C["warn"],
        "FIXME": C["err"],
        "HACK": C["err"],
        "NOTE": C["ok"],
        "XXX": C["err"],
    }

    for fname, lineno, tag, msg in all_todos[:30]:
        style = TAG_STYLE.get(tag, C["warn"])
        table.add_row(fname, str(lineno), f"[{style}]{tag}[/]", msg[:80])

    console.print(Rule(f"[{C['heading']}]◈  TODOS & FIXMES[/]", style=C["dim"]))
    console.print(table)
    if len(all_todos) > 30:
        console.print(f"  [{C['muted']}]... and {len(all_todos)-30} more[/]\n")
    console.print()


def print_functions(analyses: list[FileAnalysis], n=15):
    all_funcs = []
    for a in analyses:
        for f in a.functions:
            all_funcs.append((a.path.name, f))

    if not all_funcs:
        return

    # Sort by arg count (most complex interface first)
    all_funcs.sort(key=lambda x: len(x[1]["args"]), reverse=True)

    table = Table(
        show_header=True,
        header_style=f"bold {C['accent']}",
        border_style=C["dim"],
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("Function", style=f"bold {C['white']}", no_wrap=True)
    table.add_column("File", style=C["muted"], no_wrap=True)
    table.add_column("Line", justify="right", style=C["dim"])
    table.add_column("Args", justify="right", style=C["accent"])
    table.add_column("Flags", style=C["muted"])

    for fname, f in all_funcs[:n]:
        flags = []
        if f["is_async"]:
            flags.append(f"[{C['accent2']}]async[/]")
        if f["is_method"]:
            flags.append(f"[{C['muted']}]method[/]")
        if f["docstring"]:
            flags.append(f"[{C['ok']}]docs[/]")
        table.add_row(
            f["name"],
            fname,
            str(f["line"]),
            str(len(f["args"])),
            " ".join(flags) if flags else "[dim]—[/]",
        )

    console.print(Rule(f"[{C['heading']}]◈  TOP FUNCTIONS (by complexity)[/]", style=C["dim"]))
    console.print(table)
    console.print()


def print_errors(analyses: list[FileAnalysis]):
    errored = [(a, e) for a in analyses for e in a.errors]
    if not errored:
        return
    console.print(Rule(f"[{C['err']}]◈  PARSE ERRORS[/]", style=C["dim"]))
    for a, err in errored:
        console.print(f"  [{C['err']}]✗[/] [{C['white']}]{a.path.name}[/] — [{C['muted']}]{err}[/]")
    console.print()


def print_footer(analyses: list[FileAnalysis]):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(Rule(style=C["dim"]))
    console.print(
        f"  [{C['muted']}]CodeScope[/] [{C['dim']}]·[/] "
        f"[{C['muted']}]{len(analyses)} files analyzed[/] [{C['dim']}]·[/] "
        f"[{C['muted']}]{ts}[/]"
    )
    console.print()


# ── Entry Point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CodeScope — Python project analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python codescope.py .
  python codescope.py ./my_project --top 20
  python codescope.py . --no-todos --no-imports
  python codescope.py ./src --ignore tests migrations
        """,
    )
    parser.add_argument("path", nargs="?", default=".", help="Project root path (default: current directory)")
    parser.add_argument("--top", type=int, default=10, help="Number of top files to show (default: 10)")
    parser.add_argument("--ignore", nargs="*", default=[], help="Extra directories to ignore")
    parser.add_argument("--no-todos", action="store_true", help="Skip TODO report")
    parser.add_argument("--no-imports", action="store_true", help="Skip imports report")
    parser.add_argument("--no-functions", action="store_true", help="Skip functions report")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        console.print(f"[{C['err']}]Error:[/] Path does not exist: {root}")
        sys.exit(1)
    if not root.is_dir():
        # Single file mode
        analyses = [analyze_file(root)]
        root = root.parent
    else:
        console.print()
        analyses = scan_project(root, args.ignore)

    if not analyses:
        console.print(f"[{C['warn']}]No Python files found in:[/] {root}")
        sys.exit(0)

    print_header(root)
    print_summary(analyses, root)
    print_top_files(analyses, n=args.top)
    if not args.no_imports:
        print_imports(analyses)
    if not args.no_todos:
        print_todos(analyses)
    if not args.no_functions:
        print_functions(analyses, n=15)
    print_errors(analyses)
    print_footer(analyses)


if __name__ == "__main__":
    main()
