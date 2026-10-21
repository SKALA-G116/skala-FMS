#!/usr/bin/env python3
"""Read-only demo probes. This never approves data or declares a rehearsal complete."""
import argparse
import importlib.metadata
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def probe_json(url, timeout):
    try:
        with urlopen(url, timeout=timeout) as response:
            data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                return {'ok': False, 'error': 'response_too_large'}, None
            return {'ok': response.status == 200, 'status': response.status}, json.loads(data)
    except Exception as exc:
        return {'ok': False, 'error': type(exc).__name__}, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-url', default='http://127.0.0.1:8101')
    parser.add_argument('--model-url', default=os.getenv('FOOD_MODEL_URL', 'http://127.0.0.1:11434'))
    parser.add_argument('--model', default=os.getenv('FOOD_MODEL_NAME', 'qwen3:8b'))
    parser.add_argument('--timeout', type=float, default=3)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 0 < args.timeout <= 30:
        parser.error('timeout must be between 0 and 30 seconds')
    api, health = probe_json(args.api_url.rstrip('/') + '/health', args.timeout)
    api['ok'] = api['ok'] and isinstance(health, dict) and health.get('status') == 'ok'
    model, tags = probe_json(args.model_url.rstrip('/') + '/api/tags', args.timeout)
    names = [item.get('name') for item in tags.get('models', []) if isinstance(item, dict)] if isinstance(tags, dict) else []
    model['installed'] = args.model in names
    model['ok'] = model['ok'] and model['installed']
    model['inference_tested'] = False
    dependencies = {}
    for package in ('fastapi', 'psycopg', 'langgraph', 'fastmcp'):
        try:
            dependencies[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            dependencies[package] = None
    built = (ROOT / 'frontend/dist/index.html').is_file()
    result = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'probe_type': 'read_only', 'python': sys.version.split()[0],
        'api_health': api, 'model_installation': model,
        'frontend_built': built, 'dependencies': dependencies,
        'preflight_passed': bool(api['ok'] and model['ok'] and built and all(dependencies.values())),
        'runtime_commit': 'not_verified', 'database_apply': 'not_tested',
        'agent_end_to_end': 'not_tested', 'ocr': 'not_tested',
        'zoom_screen_share': 'not_tested', 'rehearsal_complete': False,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + '\n')
    print(output)
    return 0 if result['preflight_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
