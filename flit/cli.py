"""flit CLI — mirrors vit's command surface for FL Studio.

The CLI is the power-user / scripting path and the backend the in-app surfaces
call. Commands that touch the .flp (commit, checkout) route through flpio, which is
stubbed until the round-trip spike passes — those degrade with a clear message
rather than failing silently. Pure git/JSON commands (branch, log, status, diff)
work today.
"""

import argparse
import json
import os
import sys

from . import core, differ, json_writer, validator

try:
    from rich.console import Console
    _c = Console()
    def out(msg=""): _c.print(msg)
except ImportError:
    def out(msg=""): print(msg)


def _root() -> str:
    root = core.find_project_root()
    if not root:
        out("[red]not a flit project[/red] (no .flit found). Run `flit init`.")
        sys.exit(1)
    return root


def _flp_path(root: str) -> str:
    """Locate the project's .flp. Stored in .flit/config.json, else autodetect."""
    cfg_path = os.path.join(root, ".flit", "config.json")
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
    if cfg.get("flp"):
        return os.path.join(root, cfg["flp"])
    flps = [f for f in os.listdir(root) if f.endswith(".flp")]
    return os.path.join(root, flps[0]) if flps else ""


def cmd_init(args):
    target = os.path.abspath(args.path or ".")
    core.git_init(target)
    out(f"[green]initialized flit project[/green] at {target}")
    out("next: drop your .flp here, then `flit commit -m \"first version\"`")


def cmd_add(args):
    root = _root()
    flp = _flp_path(root)
    # Serialize the .flp if present; otherwise stage whatever JSON the engine
    # already wrote. Either way we still stage so a commit can proceed.
    if flp and os.path.exists(flp):
        try:
            from . import flpio
            proj = flpio.flp_to_project(flp)
            json_writer.write_project(root, proj)
            out("serialized .flp -> domain JSON")
        except (RuntimeError, NotImplementedError) as e:
            out(f"[yellow]serialize skipped:[/yellow] {e}")
    else:
        out("[yellow]no .flp found[/yellow] — staging existing JSON only.")
    paths = [d for d in json_writer.TRACKED_DIRS if os.path.isdir(os.path.join(root, d))]
    core.git_add(root, paths + [".flit", ".gitignore"])


def cmd_commit(args):
    root = _root()
    cmd_add(args)
    if core.git_is_clean(root):
        out("nothing to commit (no changes since last version)")
        return
    h = core.git_commit(root, args.message)
    out(f"[green]committed[/green] {h}: {args.message}")


def cmd_branch(args):
    root = _root()
    if not args.name:
        for b in core.git_list_branches(root):
            mark = "* " if b == core.git_current_branch(root) else "  "
            out(f"{mark}{b}")
        return
    core.git_branch(root, args.name)
    out(f"[green]created + switched to[/green] {args.name}")


def cmd_checkout(args):
    root = _root()
    core.git_checkout(root, args.ref)
    out(f"switched to {args.ref}")
    # restore the .flp from JSON so FL Studio opens this version
    flp = _flp_path(root)
    try:
        from . import flpio
        proj = json_writer.read_project(root)
        flpio.project_to_flp(proj, flp, flp)
        out("[green]restored .flp[/green] — reopen the project in FL Studio")
    except (RuntimeError, NotImplementedError) as e:
        out(f"[yellow].flp restore skipped:[/yellow] {e}")


def cmd_merge(args):
    root = _root()
    ok, output = core.git_merge(root, args.branch)
    out(output.strip())
    domains = json_writer.read_all_domain_files(root)
    issues = validator.validate(domains)
    out(validator.summarize(issues))
    if issues and any(i.severity == "error" for i in issues):
        out("[yellow]cross-domain issues found.[/yellow] Resolve manually, or wire "
            "ai_merge for a musical resolution. (`git merge --abort` to back out.)")


def cmd_diff(args):
    root = _root()
    ref = args.ref or "HEAD"
    base = {}
    for key, parts in [("patterns", json_writer.PATTERNS),
                       ("channels", json_writer.CHANNELS),
                       ("mixer", json_writer.MIXER),
                       ("arrangement", json_writer.ARRANGEMENT)]:
        rel = "/".join(parts)
        content = core.git_show_file(root, ref, rel)
        base[key] = json.loads(content) if content else {}
    head = json_writer.read_all_domain_files(root)
    out(differ.diff_projects(base, head))


def cmd_log(args):
    out(core.git_log(_root(), args.max_count) or "no commits yet")


def cmd_status(args):
    root = _root()
    out(f"branch: {core.git_current_branch(root)}")
    s = core.git_status(root)
    out(s if s.strip() else "clean")


def main(argv=None):
    p = argparse.ArgumentParser(prog="flit", description="git for FL Studio")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init"); sp.add_argument("path", nargs="?"); sp.set_defaults(fn=cmd_init)
    sp = sub.add_parser("add"); sp.set_defaults(fn=cmd_add)
    sp = sub.add_parser("commit"); sp.add_argument("-m", "--message", required=True); sp.set_defaults(fn=cmd_commit)
    sp = sub.add_parser("branch"); sp.add_argument("name", nargs="?"); sp.set_defaults(fn=cmd_branch)
    sp = sub.add_parser("checkout"); sp.add_argument("ref"); sp.set_defaults(fn=cmd_checkout)
    sp = sub.add_parser("merge"); sp.add_argument("branch"); sp.set_defaults(fn=cmd_merge)
    sp = sub.add_parser("diff"); sp.add_argument("ref", nargs="?"); sp.set_defaults(fn=cmd_diff)
    sp = sub.add_parser("log"); sp.add_argument("-n", "--max-count", type=int, default=20); sp.set_defaults(fn=cmd_log)
    sp = sub.add_parser("status"); sp.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
