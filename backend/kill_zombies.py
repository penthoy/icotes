
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from icpy.utils.process_reaper import reap_zombies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ManualReaper")

if __name__ == "__main__":
    print("Running manual zombie reaper...")
    # Use the broad search term
    count = reap_zombies(match_cmdline="multiprocessing", logger=logger, debug=True)
    print(f"Reaped {count} processes.")
