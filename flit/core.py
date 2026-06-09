"""Git wrapper — all git operations go through subprocess.

Ported from vit (https://github.com/LucasHJin/vit). git is tool-agnostic, so this
is nearly identical; only the .gitignore template and project markers differ.
"""

import json
import os
import subprocess
from typing import List, Optional, Tuple


class GitError(Exception):
    """Raised when a git command fails."""


def _run(args: List[str], cwd: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"git {' '.join(args)} failed: {detail}")
    return result


# flit tracks decisions (JSON + plugin sidecars), never the .flp binary, audio,
# or renders. The .flp is regenerated on checkout — like vit ignoring .drp/media.
_PROJECT_GITIGNORE = """\
# OS
.DS_Store
Thumbs.db

# FL Studio project binaries — flit regenerates these from tracked JSON
*.flp
*.flp.bak
Backup/

# Audio / renders — flit versions decisions, not media
*.wav
*.mp3
*.aiff
*.aif
*.flac
*.ogg
*.aac
Rendered/
Exported/

# Secrets / Python
.env
.env.*
__pycache__/
*.pyc
"""

_CONFIG = {"version": "0.1.0", "daw": "fl-studio"}


def _write_config(project_dir: str) -> None:
    vit_dir = os.path.join(project_dir, ".flit")
    os.makedirs(vit_dir, exist_ok=True)
    with open(os.path.join(vit_dir, "config.json"), "w") as f:
        json.dump(_CONFIG, f, indent=2, sort_keys=True)


def git_init(project_dir: str) -> None:
    """Initialize a git repo + .flit config + project dirs."""
    os.makedirs(project_dir, exist_ok=True)
    _run(["init"], cwd=project_dir)
    _write_config(project_dir)
    for d in ("timeline", "plugins", "assets"):
        os.makedirs(os.path.join(project_dir, d), exist_ok=True)
    gitignore = os.path.join(project_dir, ".gitignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w") as f:
            f.write(_PROJECT_GITIGNORE)


def git_add(project_dir: str, paths: List[str]) -> None:
    _run(["add"] + paths, cwd=project_dir)


def git_commit(project_dir: str, message: str) -> str:
    result = _run(["commit", "-m", message], cwd=project_dir)
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("["):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1].rstrip("]")
    return ""


def git_branch(project_dir: str, branch_name: str) -> None:
    _run(["checkout", "-b", branch_name], cwd=project_dir)


def git_checkout(project_dir: str, ref: str) -> None:
    _run(["checkout", ref], cwd=project_dir)


def git_merge(project_dir: str, branch: str) -> Tuple[bool, str]:
    result = _run(["merge", branch], cwd=project_dir, check=False)
    return result.returncode == 0, result.stdout + result.stderr


def git_merge_abort(project_dir: str) -> None:
    _run(["merge", "--abort"], cwd=project_dir)


def git_diff(project_dir: str, ref: Optional[str] = None) -> str:
    args = ["diff"] + ([ref] if ref else [])
    return _run(args, cwd=project_dir).stdout


def git_log(project_dir: str, max_count: int = 20) -> str:
    return _run(
        ["log", f"--max-count={max_count}", "--oneline", "--decorate"], cwd=project_dir
    ).stdout


def git_status(project_dir: str) -> str:
    return _run(["status", "--short"], cwd=project_dir).stdout


def git_current_branch(project_dir: str) -> str:
    return _run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=project_dir).stdout.strip()


def git_list_branches(project_dir: str) -> List[str]:
    out = _run(["branch", "--list"], cwd=project_dir).stdout
    return [ln.strip().lstrip("* ") for ln in out.splitlines() if ln.strip()]


def git_show_file(project_dir: str, ref: str, filepath: str) -> Optional[str]:
    result = _run(["show", f"{ref}:{filepath}"], cwd=project_dir, check=False)
    return result.stdout if result.returncode == 0 else None


def git_merge_base(project_dir: str, ref1: str, ref2: str) -> Optional[str]:
    result = _run(["merge-base", ref1, ref2], cwd=project_dir, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def git_list_conflicted_files(project_dir: str) -> List[str]:
    result = _run(
        ["diff", "--name-only", "--diff-filter=U"], cwd=project_dir, check=False
    )
    return [f for f in result.stdout.splitlines() if f.strip()]


def git_is_clean(project_dir: str) -> bool:
    result = _run(["status", "--porcelain"], cwd=project_dir, check=False)
    return not result.stdout.strip()


def is_git_repo(project_dir: str) -> bool:
    if not os.path.isdir(project_dir):
        return False
    return _run(["rev-parse", "--git-dir"], cwd=project_dir, check=False).returncode == 0


def find_project_root(start_dir: Optional[str] = None) -> Optional[str]:
    current = start_dir or os.getcwd()
    while True:
        if os.path.isdir(os.path.join(current, ".flit")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def git_push(project_dir: str, remote: str = "origin", branch: Optional[str] = None) -> str:
    args = ["push", remote] + ([branch] if branch else [])
    return _run(args, cwd=project_dir).stdout


def git_pull(project_dir: str, remote: str = "origin", branch: Optional[str] = None) -> str:
    args = ["pull", remote] + ([branch] if branch else [])
    return _run(args, cwd=project_dir).stdout
