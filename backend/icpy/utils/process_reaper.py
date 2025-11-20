"""
Process Reaper Utility

Handles cleanup of stuck child processes, particularly multiprocessing spawns
that can leak memory and cause server freezes.
"""

import os
import signal
import logging

logger = logging.getLogger(__name__)

def reap_zombies(match_cmdline: str = "multiprocessing", logger: logging.Logger = None, debug: bool = False) -> int:
    """
    Kill user-owned processes whose cmdline contains match_cmdline.
    Default targets generic 'multiprocessing' to catch spawn/resource_tracker.
    
    Args:
        match_cmdline: Substring to look for in the process command line.
        logger: Optional logger to use. If None, uses module logger.
        debug: If True, logs detailed info about scanned processes.
        
    Returns:
        Number of processes killed.
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    try:
        my_pid = os.getpid()
        killed_count = 0
        
        if not os.path.exists("/proc"):
            logger.warning("[ProcessReaper] /proc not available, cannot reap zombies")
            return 0
            
        if debug:
            logger.info(f"[ProcessReaper] Starting scan for '{match_cmdline}' (my_pid={my_pid})")
            
        # Collect candidates first to avoid side effects during iteration
        candidates = []
        
        # Iterate over all processes in /proc
        for pid_str in os.listdir("/proc"):
            if not pid_str.isdigit():
                continue
                
            pid = int(pid_str)
            if pid == my_pid:
                continue
                
            try:
                # Check parent PID using /proc/<pid>/stat
                # Format: pid (comm) state ppid ...
                try:
                    with open(f"/proc/{pid}/stat", "r") as f:
                        stat = f.read()
                except FileNotFoundError:
                    continue # Process gone
                
                # Parse stat file safely (comm can contain parens)
                rparen_index = stat.rfind(')')
                if rparen_index == -1:
                    continue
                    
                rest = stat[rparen_index+1:].strip()
                fields = rest.split()
                if len(fields) < 2:
                    continue
                    
                ppid = int(fields[1])
                
                # Check command line
                try:
                    with open(f"/proc/{pid}/cmdline", "r") as f:
                        cmdline = f.read()
                    
                    # cmdline is null-separated, replace with spaces for matching
                    cmdline_clean = cmdline.replace('\0', ' ')
                    
                    if match_cmdline in cmdline_clean:
                        # Verify ownership to avoid killing other users' processes
                        try:
                            proc_uid = os.stat(f"/proc/{pid}").st_uid
                            my_uid = os.getuid()
                            
                            if proc_uid == my_uid:
                                candidates.append((pid, ppid, cmdline_clean))
                            elif debug:
                                logger.info(f"[ProcessReaper] Skipped {pid}: UID mismatch ({proc_uid} != {my_uid})")
                        except (FileNotFoundError, ProcessLookupError):
                            continue
                    elif debug:
                         # Log all python-related processes for debugging
                         if any(x in cmdline_clean for x in ["python", "uvicorn", "icpy", "multiprocessing"]):
                             logger.info(f"[ProcessReaper] Skipped {pid}: cmdline mismatch '{cmdline_clean}'")

                except FileNotFoundError:
                    if debug:
                        logger.debug(f"[ProcessReaper] Could not read cmdline for {pid}")
                    continue
            except Exception as e:
                # Ignore permission errors etc.
                if debug:
                    logger.debug(f"[ProcessReaper] Error scanning {pid}: {e}")
                continue
        
        # Kill all candidates
        for pid, ppid, cmdline_clean in candidates:
            try:
                logger.warning(f"[ProcessReaper] Killing stuck process {pid} (ppid={ppid}): {cmdline_clean[:100]}...")
                os.kill(pid, signal.SIGKILL) # Force kill
                killed_count += 1
            except ProcessLookupError:
                logger.info(f"[ProcessReaper] Process {pid} already gone")
            except Exception as e:
                logger.error(f"[ProcessReaper] Failed to kill {pid}: {e}")
                    
        if killed_count > 0:
            logger.info(f"[ProcessReaper] Reaped {killed_count} zombie processes")
        elif debug:
            logger.info("[ProcessReaper] Scan complete, no zombies found")
            
        return killed_count
        
    except Exception as e:
        logger.error(f"[ProcessReaper] Error reaping zombies: {e}")
        return 0

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    # Default to "multiprocessing" if no arg provided
    pattern = sys.argv[1] if len(sys.argv) > 1 else "multiprocessing"
    count = reap_zombies(match_cmdline=pattern, debug=True)
    print(f"Reaped {count} processes")
