#!/usr/bin/env python3
"""
bag_tool.py — Export and compare .bag file inventories.

Export mode:
    python bag_tool.py export --path <dir> [--output bag_list.txt]

Compare mode:
    python bag_tool.py compare --txt <bag_list.txt> --path <dir> [--output report.txt]
"""

import os
import sys
import argparse
from datetime import datetime


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024 or unit == "TB":
            return f"{size_bytes:.2f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024


def scan_bags(directory: str) -> dict[str, list[tuple[str, int, str]]]:
    """Return {filename: [(abs_path, size_bytes, mtime_str), ...]} for all .bag files under directory."""
    result: dict[str, list[tuple[str, int, str]]] = {}
    for root, _, files in os.walk(directory):
        for fname in files:
            if fname.lower().endswith(".bag"):
                abs_path = os.path.abspath(os.path.join(root, fname))
                size = os.path.getsize(abs_path)
                mtime = datetime.fromtimestamp(os.path.getmtime(abs_path)).strftime("%Y-%m-%d %H:%M:%S")
                result.setdefault(fname, []).append((abs_path, size, mtime))
    return result


def cmd_export(args: argparse.Namespace) -> None:
    path = os.path.abspath(args.path)
    if not os.path.isdir(path):
        sys.exit(f"Error: '{path}' is not a directory.")

    bag_map = scan_bags(path)
    duplicates = {f: entries for f, entries in bag_map.items() if len(entries) > 1}
    if duplicates:
        print(f"Warning: {len(duplicates)} filename(s) appear more than once in '{path}':")
        for fname, entries in duplicates.items():
            for p, _, _ in entries:
                print(f"  {p}")

    output = os.path.abspath(args.output)
    total_files = sum(len(v) for v in bag_map.values())
    total_bytes = sum(s for entries in bag_map.values() for _, s, _ in entries)

    with open(output, "w", encoding="utf-8") as f:
        f.write(f"# exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# source: {path}\n")
        f.write("# path\tfilename\tsize_bytes\tmtime\n")
        for entries in bag_map.values():
            for abs_path, size, mtime in sorted(entries):
                fname = os.path.basename(abs_path)
                f.write(f"{abs_path}\t{fname}\t{size}\t{mtime}\n")

    print(f"Exported {total_files} bag file(s) ({_human_size(total_bytes)}) -> {output}")


def parse_txt(txt_path: str) -> dict[str, int]:
    """Parse exported txt. Returns {filename: size_bytes}. Supports 3-col and 4-col (with mtime) formats."""
    result: dict[str, int] = {}
    duplicates: list[str] = []
    with open(txt_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) not in (3, 4):
                print(f"Warning: skipping malformed line: {line!r}")
                continue
            _, fname, size_str = parts[0], parts[1], parts[2]
            try:
                size = int(size_str)
            except ValueError:
                print(f"Warning: skipping line with non-integer size: {line!r}")
                continue
            if fname in result:
                duplicates.append(fname)
            result[fname] = size
    if duplicates:
        print(f"Warning: {len(duplicates)} duplicate filename(s) in txt (last value kept): {duplicates}")
    return result


def cmd_compare(args: argparse.Namespace) -> None:
    txt_path = os.path.abspath(args.txt)
    if not os.path.isfile(txt_path):
        sys.exit(f"Error: txt file '{txt_path}' not found.")

    compare_dir = os.path.abspath(args.path)
    if not os.path.isdir(compare_dir):
        sys.exit(f"Error: '{compare_dir}' is not a directory.")

    reference = parse_txt(txt_path)
    bag_map = scan_bags(compare_dir)

    # Flatten bag_map to {filename: (size, mtime)} (warn on local duplicates, keep first)
    actual: dict[str, tuple[int, str]] = {}
    local_dups: list[str] = []
    for fname, entries in bag_map.items():
        if len(entries) > 1:
            local_dups.append(fname)
        actual[fname] = (entries[0][1], entries[0][2])
    if local_dups:
        print(f"Warning: {len(local_dups)} filename(s) appear more than once in '{compare_dir}' (first occurrence used).")

    missing = {f: s for f, s in reference.items() if f not in actual}
    mismatched = {
        f: (reference[f], actual[f][0])
        for f in reference
        if f in actual and reference[f] != actual[f][0]
    }
    extra = {f: actual[f] for f in actual if f not in reference}
    ok_count = len(reference) - len(missing) - len(mismatched)

    output = os.path.abspath(args.output)
    with open(output, "w", encoding="utf-8") as f:
        f.write(f"# bag_tool compare report\n")
        f.write(f"# generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# reference txt : {txt_path}\n")
        f.write(f"# compare path  : {compare_dir}\n")
        f.write(f"# total in ref  : {len(reference)}\n")
        f.write(f"# matched OK    : {ok_count}\n")
        f.write(f"# missing       : {len(missing)}\n")
        f.write(f"# size mismatch : {len(mismatched)}\n")
        f.write(f"# extra in dest : {len(extra)}\n")
        f.write("\n")

        f.write("=" * 60 + "\n")
        f.write("MISSING BAGS\n")
        f.write("=" * 60 + "\n")
        if missing:
            for fname, expected in sorted(missing.items()):
                f.write(f"  {fname}  (expected size: {_human_size(expected)} / {expected} B)\n")
        else:
            f.write("  (none)\n")

        f.write("\n")
        f.write("=" * 60 + "\n")
        f.write("SIZE MISMATCH\n")
        f.write("=" * 60 + "\n")
        if mismatched:
            f.write(f"  {'filename':<40}  {'expected':>16}  {'actual':>16}  {'delta':>16}  {'mtime (dest)':>19}\n")
            f.write(f"  {'-'*40}  {'-'*16}  {'-'*16}  {'-'*16}  {'-'*19}\n")
            for fname, (exp, act) in sorted(mismatched.items()):
                delta = act - exp
                sign = "+" if delta >= 0 else ""
                mtime = actual[fname][1]
                f.write(
                    f"  {fname:<40}  {_human_size(exp):>16}  {_human_size(act):>16}  "
                    f"{sign}{_human_size(abs(delta)):>15}  {mtime:>19}\n"
                )
        else:
            f.write("  (none)\n")

        f.write("\n")
        f.write("=" * 60 + "\n")
        f.write("EXTRA BAGS (in dest only)\n")
        f.write("=" * 60 + "\n")
        if extra:
            for fname, (size, mtime) in sorted(extra.items()):
                f.write(f"  {fname}  (size: {_human_size(size)} / {size} B  mtime: {mtime})\n")
        else:
            f.write("  (none)\n")

    print(
        f"Compare result: {len(reference)} reference | "
        f"{ok_count} OK | {len(missing)} missing | {len(mismatched)} size mismatch | "
        f"{len(extra)} extra in dest"
    )
    print(f"Report written -> {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export or compare .bag file inventories."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    exp = sub.add_parser("export", help="Scan a directory and export bag inventory to txt.")
    exp.add_argument("--path", required=True, help="Directory to scan.")
    exp.add_argument("--output", default="bag_list.txt", help="Output txt file (default: bag_list.txt).")

    cmp = sub.add_parser("compare", help="Compare a directory against a reference txt.")
    cmp.add_argument("--txt", required=True, help="Reference txt file produced by export mode.")
    cmp.add_argument("--path", required=True, help="Directory to compare against.")
    cmp.add_argument("--output", default="report.txt", help="Output report file (default: report.txt).")

    args = parser.parse_args()
    if args.command == "export":
        cmd_export(args)
    else:
        cmd_compare(args)


if __name__ == "__main__":
    main()
