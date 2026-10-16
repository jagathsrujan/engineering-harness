from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .graph.ids import IdKind, kind_of
from .graph.io import load_project
from .graph.model import GraphError
from .history.journal import Journal
from .persistence import mirror
from .solver.drivers import sweep
from .solver.report import build_report, format_report, report_to_dict, verify_exit_code
from .solver.solve import run as run_solver


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness", description="parametric graph harness")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("project", help="project directory (or main.yaml)")
        return p

    add("load", "load and validate a project graph")
    add("solve", "solve the graph (all nodes)")
    report_parser = add("report", "human-readable state report")
    report_parser.add_argument("--json", action="store_true")
    add("verify", "check sweep: runs report and exits non-zero on violations")
    add("undo", "undo the last applied change")
    sweep_parser = sub.add_parser("sweep", help="what-if sweep over a parameter")
    sweep_parser.add_argument("project")
    sweep_parser.add_argument("parameter")
    sweep_parser.add_argument("--start", type=float, required=True)
    sweep_parser.add_argument("--stop", type=float, required=True)
    sweep_parser.add_argument("--steps", type=int, default=10)

    args = parser.parse_args(argv)
    path = Path(args.project)
    try:
        project = load_project(path)
    except Exception as err:
        print(f"load failed: {err}", file=sys.stderr)
        return 2

    if args.command == "load":
        counts = (
            f"components={len(project.components)} parameters={len(project.params)} "
            f"relations={len(project.relations)} constraints={len(project.constraints)} "
            f"requirements={len(project.requirements)} decisions={len(project.decisions)} "
            f"unknowns={len(project.unknowns)} test_results={len(project.test_results)}"
        )
        print(f"ok: {project.id} ({project.name}) -> {counts}")
        return 0

    if args.command == "solve":
        result = run_solver(project)
        mirror.rebuild(project)
        unsolved = result.unsolved
        summary = (
            f"solved {project.id}: steps={result.plan_steps} "
            f"recomputed={len(result.recompute_set)} unsolved={len(unsolved)}"
        )
        print(summary)
        for parameter_id in sorted(unsolved):
            print(f"  UNSOLVED {parameter_id}: {unsolved[parameter_id]}")
        return 0

    if args.command == "report":
        result = run_solver(project)
        report = build_report(project, result)
        payload = report_to_dict(report)
        print(json.dumps(payload, ensure_ascii=False) if getattr(args, "json", False) else format_report(report))
        return 0

    if args.command == "verify":
        result = run_solver(project)
        report = build_report(project, result)
        print(format_report(report))
        print()
        db = mirror.rebuild(project)
        print(f"mirror: {mirror.count_nodes(db)} nodes in {db}")
        return verify_exit_code(report)

    if args.command == "undo":
        journal = Journal(project)
        seq = journal.undo()
        if seq is None:
            print("nothing to undo")
            return 1
        print(f"undid change seq={seq}")
        return 0

    if args.command == "sweep":
        try:
            if kind_of(args.parameter) != IdKind.PARAMETER:
                raise GraphError(f"{args.parameter!r} is not a parameter id")
            records = sweep(
                project,
                args.parameter,
                args.start,
                args.stop,
                args.steps,
            )
        except (ValueError, GraphError, LookupError) as err:
            print(f"sweep failed: {err}", file=sys.stderr)
            return 2
        for record in records:
            print(
                json.dumps(
                    {k: v for k, v in record.items() if k not in ("values",) and v is not None}, ensure_ascii=False
                )
            )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
