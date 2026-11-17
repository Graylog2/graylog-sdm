#! /usr/bin/python3
import argparse
import logging

from pathlib import Path

from runner import run_build


BASE_DIR = Path(__file__).resolve().parent

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build GIM tables and docs')

    parser.add_argument(
        '-ll', '--loglevel',
        help='Logging level',
        type=str,
        default='info',
        choices=['debug', 'info', 'warning', 'error', 'critical']
    )

    parser.add_argument(
        '-c', '--config_dir',
        help='Path to configuration files',
        type=str,
        default='configs'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate output generation without writing files'
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper()),
        format='%(asctime)s %(levelname)s [%(name)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    config_dir = BASE_DIR / Path(args.config_dir)
    if not config_dir.is_dir():
        logging.fatal('Config directory %s is not a directory or does not exist', config_dir)
        exit(1)

    repo_dir = Path(__file__).resolve().parents[2]
    run_build(repo_dir, config_dir, dry_run=args.dry_run)
