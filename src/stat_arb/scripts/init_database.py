#!/usr/bin/env python3
"""
Database initialization script for the Structured Registry.

This script initializes the SQLite database with all required tables.

Usage:
    uv run python -m stat_arb.scripts.init_database [--db-path PATH] [--drop-existing]

Requirements: 9.1-9.11, 27.14
"""

import argparse
import logging
import sys
from pathlib import Path

from stat_arb.storage import DEFAULT_DB_PATH, init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """
    Main entry point for database initialization.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Initialize the Structured Registry database."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop all existing tables before creating new ones (WARNING: deletes all data!)",
    )

    args = parser.parse_args()

    try:
        logger.info("Starting database initialization...")
        logger.info(f"Database path: {args.db_path}")

        if args.drop_existing:
            logger.warning("WARNING: --drop-existing flag is set. All data will be deleted!")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Database initialization cancelled.")
                return 0

        # Initialize the database
        engine = init_database(db_path=args.db_path, drop_existing=args.drop_existing)

        logger.info("Database initialization successful!")
        logger.info(f"Database created at: {args.db_path.resolve()}")

        # Close the engine
        engine.dispose()

        return 0

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
