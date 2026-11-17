"""Command-line interface for build-sdm."""

import argparse
import logging
from pathlib import Path

from build_sdm.runner import run_build
from build_sdm.utils.paths import find_repo_root

__all__ = ["DEFAULT_CONFIG_DIR", "build_parser", "main"]

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent / "configs"

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the build-sdm argument parser.

    Returns:
        The configured parser with one subparser per command.
    """
    parser = argparse.ArgumentParser(
        prog="build-sdm", description="Build Graylog Security Data Model (SDM) tables and docs"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build all enabled output plugins")
    build.add_argument(
        "-ll",
        "--loglevel",
        help="Logging level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
    )
    build.add_argument(
        "-c",
        "--config_dir",
        help="Path to configuration files; relative paths resolve against the current directory "
        "(default: the package's configs/)",
        type=Path,
        default=DEFAULT_CONFIG_DIR,
    )
    build.add_argument(
        "--dry-run", action="store_true", help="Simulate output generation without writing files"
    )
    return parser


def _configure_logging(level: str) -> None:
    """Configure root logging in the format the build has always used.

    Args:
        level: Log level name, e.g. "info".
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _cmd_build(args: argparse.Namespace) -> int:
    """Run the build command.

    Args:
        args: Parsed arguments for the build subcommand.

    Returns:
        Process exit code.
    """
    config_dir = args.config_dir.resolve()
    if not config_dir.is_dir():
        logger.fatal("Config directory %s is not a directory or does not exist", config_dir)
        return 1

    try:
        run_build(find_repo_root(), config_dir, dry_run=args.dry_run)
    except Exception:
        # Plugin and loader failures are fatal (ADR 0002); report once at the boundary.
        logger.critical("Build failed", exc_info=True)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the build-sdm console script.

    Args:
        argv: Arguments to parse. Defaults to sys.argv[1:].

    Returns:
        Process exit code.
    """
    args = build_parser().parse_args(argv)
    _configure_logging(args.loglevel)
    return _cmd_build(args)
