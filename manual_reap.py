
import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from icpy.utils.process_reaper import reap_zombies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ManualReaper")

print("Scanning for zombies...")
count = reap_zombies(match_cmdline="multiprocessing", logger=logger, debug=True)
print(f"Reaped {count} zombies.")
