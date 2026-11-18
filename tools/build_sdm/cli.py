"""Command-line interface for build-sdm."""

import argparse
import logging
import shlex
import tempfile
from pathlib import Path

from build_sdm.check_generated import compare_trees, format_diff
from build_sdm.config_loader import load_script_config_files
from build_sdm.runner import run_build
from build_sdm.utils.paths import find_repo_root

__all__ = ["DEFAULT_CONFIG_DIR", "MADCAP_PLUGIN", "build_parser", "main"]

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent / "configs"
MADCAP_PLUGIN = "MadcapHtmlOutput"

logger = logging.getLogger(__name__)


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    """Add the logging and config-dir options every build-running subcommand takes.

    Args:
        parser: Subcommand parser to extend.
    """
    parser.add_argument(
        "-ll",
        "--loglevel",
        help="Logging level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
    )
    parser.add_argument(
        "-c",
        "--config_dir",
        help="Path to configuration files; relative paths resolve against the current directory "
        "(default: the package's configs/)",
        type=Path,
        default=DEFAULT_CONFIG_DIR,
    )


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
    _add_common_options(build)
    build.add_argument(
        "--dry-run", action="store_true", help="Simulate output generation without writing files"
    )
    build.add_argument(
        "--madcap-output-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write the MadCap HTML only to PATH (relative paths resolve against the current "
        "directory). Overrides the MadCap plugin's output_dir config.",
    )

    check = subparsers.add_parser(
        "check-generated",
        help="Check that the committed MadCap output matches a fresh build",
        description="Build into a temporary directory and compare the MadCap HTML byte for byte "
        "with the committed copy (the MadCap plugin's configured output_dir). Exits 1 if any "
        "file is changed, stale or missing.",
    )
    _add_common_options(check)

    subparsers.add_parser("validate", help="Validate SDM source data (not implemented until PR 3)")
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


def _resolve_config_dir(config_dir: Path) -> Path | None:
    """Resolve the config directory, logging if it doesn't exist.

    Args:
        config_dir: The --config_dir value.

    Returns:
        The absolute config directory, or None if it isn't a directory.
    """
    resolved = config_dir.resolve()
    if not resolved.is_dir():
        logger.fatal("Config directory %s is not a directory or does not exist", resolved)
        return None
    return resolved


def _cmd_build(args: argparse.Namespace) -> int:
    """Run the build command.

    Args:
        args: Parsed arguments for the build subcommand.

    Returns:
        Process exit code.
    """
    config_dir = _resolve_config_dir(args.config_dir)
    if config_dir is None:
        return 1

    overrides = {}
    if args.madcap_output_dir is not None:
        overrides[MADCAP_PLUGIN] = args.madcap_output_dir.resolve()

    try:
        run_build(find_repo_root(), config_dir, dry_run=args.dry_run, output_dir_overrides=overrides)
    except Exception:
        # Plugin and loader failures are fatal (ADR 0002); report once at the boundary.
        logger.critical("Build failed", exc_info=True)
        return 1
    return 0


def _committed_madcap_dir(config_dir: Path, repo_root: Path) -> Path | None:
    """Return the MadCap plugin's configured output_dir, resolved against the repo root.

    Args:
        config_dir: Script config directory.
        repo_root: Repository root.

    Returns:
        The committed MadCap output directory, or None if none is configured.
    """
    plugin = load_script_config_files(config_dir).get("plugins", {}).get(MADCAP_PLUGIN, {})
    configured = plugin.get("output_dir")
    if not configured:
        return None
    path = Path(str(configured))
    return path if path.is_absolute() else repo_root / path


def _display_path(path: Path, repo_root: Path) -> str:
    """Return path relative to the repo root when it is inside it, else as given.

    Args:
        path: Path to display.
        repo_root: Repository root.

    Returns:
        The path as a string for messages.
    """
    return path.relative_to(repo_root).as_posix() if path.is_relative_to(repo_root) else str(path)


def _build_command(config_dir: Path, repo_root: Path) -> str:
    """Return the build command that reproduces a check run with config_dir.

    Args:
        config_dir: The resolved config directory the check used.
        repo_root: Repository root.

    Returns:
        The command, with --config_dir only when it isn't the default.
    """
    command = "uv run build-sdm build"
    if config_dir == DEFAULT_CONFIG_DIR:
        return command
    return f"{command} --config_dir {shlex.quote(_display_path(config_dir, repo_root))}"


def _cmd_check_generated(args: argparse.Namespace) -> int:
    """Run the check-generated command.

    Args:
        args: Parsed arguments for the check-generated subcommand.

    Returns:
        0 if the committed MadCap output matches a fresh build, 1 otherwise.
    """
    config_dir = _resolve_config_dir(args.config_dir)
    if config_dir is None:
        return 1
    repo_root = find_repo_root()
    committed = _committed_madcap_dir(config_dir, repo_root)
    if committed is None:
        logger.fatal("%s has no output_dir configured; nothing to check", MADCAP_PLUGIN)
        return 1

    with tempfile.TemporaryDirectory(prefix="build-sdm-check-") as tmp:
        fresh = Path(tmp) / MADCAP_PLUGIN
        try:
            # Everything goes to the temporary directory, so the check leaves build/ alone.
            run_build(
                repo_root,
                config_dir,
                output_dir_overrides={MADCAP_PLUGIN: fresh},
                output_root=Path(tmp) / "other",
            )
        except Exception:
            logger.critical("Build failed", exc_info=True)
            return 1
        diff = compare_trees(committed, fresh)

    display = _display_path(committed, repo_root)
    if diff.clean:
        logger.info("%s is up to date", display)
        return 0
    print(format_diff(diff, display, _build_command(config_dir, repo_root)))
    return 1


def _cmd_validate(_args: argparse.Namespace) -> int:
    """Placeholder for the validate command, implemented in PR 3.

    Args:
        _args: Parsed arguments (unused).

    Returns:
        2, so a pipeline calling it cannot mistake it for a passing check.
    """
    print("build-sdm validate is not implemented yet (planned for PR 3).")
    return 2


def main(argv: list[str] | None = None) -> int:
    """Entry point for the build-sdm console script.

    Args:
        argv: Arguments to parse. Defaults to sys.argv[1:].

    Returns:
        Process exit code.
    """
    args = build_parser().parse_args(argv)
    _configure_logging(getattr(args, "loglevel", "info"))
    if args.command == "check-generated":
        return _cmd_check_generated(args)
    if args.command == "validate":
        return _cmd_validate(args)
    return _cmd_build(args)
