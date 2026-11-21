from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter the final V1 live audit records")
    parser.add_argument("--results", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    wanted = {
        run["audit_id"]
        for scene in results.get("scenes", [])
        for run in scene.get("runs", [])
        if isinstance(run.get("audit_id"), str)
    }

    records = [
        json.loads(line)
        for line in Path(args.audit).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [record for record in records if record.get("audit_id") in wanted]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            for record in selected
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "requested_audit_ids": len(wanted),
                "source_records": len(records),
                "selected_records": len(selected),
                "output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
