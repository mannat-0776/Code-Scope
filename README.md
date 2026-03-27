# ◈ CodeScope

A dark, terminal-native Python project analyzer. Run it on any Python codebase and get an instant rich report — file sizes, function breakdown, import graph, TODO tracker, and complexity scores.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python) ![rich](https://img.shields.io/badge/rich-terminal_UI-orange?style=flat-square) ![Zero Config](https://img.shields.io/badge/zero-config-64ffda?style=flat-square)

---

## ✦ What It Shows

| Section | Details |
|---|---|
| **Project Summary** | Files, total/code/comment/blank lines, classes, functions, avg complexity |
| **Top Files** | Ranked by size with inline bar chart, complexity score, TODO count |
| **Top Imports** | stdlib vs third-party, usage frequency |
| **TODOs & FIXMEs** | File, line number, tag type, message — `TODO / FIXME / HACK / NOTE` |
| **Top Functions** | Ranked by argument count, async flags, docstring presence |
| **Parse Errors** | Any files with syntax errors |

---

## 🚀 Install & Run

```bash
git clone https://github.com/yourusername/codescope.git
cd codescope
pip install rich
```

```bash
# Analyze current directory
python codescope.py .

# Analyze a specific project
python codescope.py ~/projects/my-app

# Single file
python codescope.py app.py

# Custom options
python codescope.py ./src --top 20 --ignore tests migrations
```

---

## ⚙️ Options

```
usage: codescope.py [path] [options]

positional arguments:
  path              Project root path (default: current directory)

options:
  --top N           Number of top files to show (default: 10)
  --ignore DIR ...  Extra directories to ignore
  --no-todos        Skip TODO/FIXME report
  --no-imports      Skip imports report
  --no-functions    Skip functions report
```

---

## 📸 Output Preview

```
╭──────────────────────────────────────────────╮
│  CodeScope ◈  Python Project Analyzer        │
│  /home/user/my-project                       │
╰──────────────────────────────────────────────╯

──────────── ◈  PROJECT SUMMARY ────────────
  Files:        12   Functions:    47
  Total lines:  2341  Classes:     8
  Code lines:   1890  TODOs:       3
  Avg complexity: 6.2  Errors:     0

──────────── ◈  TOP FILES BY SIZE ──────────
  ████████████ app.py          342  lines
  ████████░░░░ models.py       280  lines
  ██████░░░░░░ utils.py        210  lines
  ...
```

---

## 🛠 How It Works

- Uses Python's built-in `ast` module to parse each file without executing it
- Walks the AST tree to count functions, classes, imports, and branches (complexity)
- Counts branch nodes (`if`, `for`, `while`, `try`, `with`) for cyclomatic complexity estimate
- Uses `rich` for all terminal rendering — tables, panels, progress bar, colored output

---

## 📁 Structure

```
codescope/
└── codescope.py    # single file, no config needed
```

---

## Requirements

- Python 3.8+
- `rich` (`pip install rich`)

---

Made with ◈ by [Mannat](https://github.com/mannatwalia-0776)
