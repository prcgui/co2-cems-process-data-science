"""Entrada comum para execução portátil com Python."""
import argparse
from pathlib import Path
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['audit', 'reference', 'baseline', 'experiment', 'report'])
    parser.add_argument('--root', type=Path, default=Path(os.environ.get('IATAN_PROJECT_ROOT', Path.cwd())))
    parser.add_argument('--config', type=Path)
    args = parser.parse_args(); root = args.root.resolve()
    if args.command == 'audit':
        from .data import freeze
        print(freeze(root))
    elif args.command == 'reference':
        from .baseline import verify_frozen_reference
        print(verify_frozen_reference(root))
    elif args.command == 'baseline':
        from .baseline import run
        print(run(root))
    elif args.command == 'experiment':
        from .experiments import run
        print(run(root, args.config))
    else:
        from .report import build
        from .tracking import portable_path
        print(portable_path(build(root), root))


if __name__ == '__main__': main()
