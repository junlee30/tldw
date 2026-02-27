"""TL;DW: Convert YouTube videos into shareable visual story summaries."""

import argparse
import logging
import sys
import webbrowser

from core.pipeline import run_pipeline, PipelineError


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )
    # Quiet noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="tldw",
        description="TL;DW — YouTube video visual summaries",
    )
    parser.add_argument(
        "url",
        help="YouTube video URL",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't open the result in the browser",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        result = run_pipeline(args.url)

        print(f"\nSummary generated: {result.html_path}")
        print(f"  {len(result.card_paths)} cards · OG image · analysis cached")

        if not args.no_open:
            webbrowser.open(result.html_path.as_uri())

        return 0

    except PipelineError as e:
        logging.error(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        logging.info("\nCancelled.")
        return 130
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
