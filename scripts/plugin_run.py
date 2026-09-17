#!/usr/bin/env python3
"""Versioned, offline JSON interface. No network or model calls."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
MAX_BYTES = 1_000_000

def execute(data: dict) -> dict:
    from stage2_generate_timeline import generate_timeline, invalid_time_reason, load_yaml, TIMELINE_FIELDS
    import csv, io
    rows = data["material_rows"]
    rejected = [{"row": index + 1, "reason": reason} for index, row in enumerate(rows) if (reason := invalid_time_reason(row))]
    timeline = generate_timeline(rows, load_yaml(ROOT / "configs/editing_rules.yaml"), load_yaml(ROOT / "configs/user_preferences.yaml"))
    stream = io.StringIO(); writer = csv.DictWriter(stream, fieldnames=TIMELINE_FIELDS); writer.writeheader(); writer.writerows(timeline)
    return {"markdown": "# Timeline review\n\nReview every cut and risk_note before rendering. No media was read or rendered.\n", "csv": stream.getvalue(), "timeline": timeline, "clip_count": len(timeline), "total_duration_seconds": round(sum(row["duration_seconds"] for row in timeline), 3), "rejected_rows": rejected, "requires_human_review": True}


def run(data: dict) -> dict:
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / "schemas/input.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(data)
    result = {"schema_version": "1.0", "status": "ok", "mode": 'timeline_only', "result": execute(data), "warnings": ['仅依据输入索引和规则排序，不读取媒体、不运行 ASR、不渲染视频。', '质量与语义分数来自输入，不代表本次进行了模型评估。']}
    Draft202012Validator(json.loads((ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))).validate(result)
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description='从素材索引生成可人工复核的粗剪时间线')
    parser.add_argument("--input", type=Path, help="UTF-8 JSON file. Omit to read stdin.")
    parser.add_argument("--output-dir", type=Path, help="New directory inside output/. Existing directories are never overwritten.")
    args = parser.parse_args()
    try:
        if args.input and args.input.stat().st_size > MAX_BYTES: raise ValueError("Input exceeds 1 MB")
        raw = args.input.read_text(encoding="utf-8-sig") if args.input else sys.stdin.buffer.read(MAX_BYTES + 1).decode("utf-8-sig")
        if len(raw.encode("utf-8")) > MAX_BYTES: raise ValueError("Input exceeds 1 MB")
        data = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON number")))
        payload = run(data)
        if args.output_dir:
            destination = args.output_dir.resolve()
            allowed = (ROOT / "output").resolve()
            if not destination.is_relative_to(allowed) or destination == allowed:
                raise ValueError("Choose a new subdirectory inside output/")
            destination.mkdir(parents=True, exist_ok=False)
            (destination / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (destination / "result.md").write_text(payload["result"]["markdown"], encoding="utf-8")
            if "csv" in payload["result"]: (destination / "timeline.csv").write_text(payload["result"]["csv"], encoding="utf-8")
        code = 0
    except ImportError:
        payload = {"schema_version":"1.0", "status":"error", "error":{"code":"DEPENDENCY_MISSING", "message":"Install requirements-plugin.txt before running the plugin."}}
        code = 2
    except Exception as exc:
        # Do not echo user text, stack traces or local file paths into the response.
        if type(exc).__name__ == "ValidationError":
            location = ".".join(str(part) for part in exc.absolute_path) or "input"
            message = f"Invalid field: {location}; failed {exc.validator} constraint. See schemas/input.schema.json."
        elif isinstance(exc, (FileExistsError, FileNotFoundError, PermissionError, OSError)):
            message = "Cannot read input or create a fresh output directory. Existing output is preserved."
        elif isinstance(exc, json.JSONDecodeError): message = "Input must be valid UTF-8 JSON."
        else: message = str(exc) if isinstance(exc, ValueError) else "Generation failed; check the documented input contract."
        payload = {"schema_version":"1.0", "status":"error", "error":{"code":"INVALID_INPUT_OR_OUTPUT", "message":message}}
        code = 2
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
