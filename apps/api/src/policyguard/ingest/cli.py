from __future__ import annotations

import argparse
import sys
from pathlib import Path

from policyguard.config import get_settings

from .indexer import build_index


def _parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Build the NovaCart policy index.")
    parser.add_argument("--policies", type=Path, default=settings.policies_dir)
    parser.add_argument("--out", type=Path, default=settings.index_dir)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = build_index(args.policies, args.out)
    except Exception as exc:
        print(f"index build failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"indexed {manifest.document_count} documents, "
        f"{manifest.chunk_count} chunks, "
        f"quarantined {len(manifest.quarantined_lines)} instruction lines"
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
