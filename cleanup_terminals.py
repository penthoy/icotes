#!/usr/bin/env python3
"""
Cleanup script to remove stale terminal sessions
"""

import requests
import json

def cleanup_terminals():
    """Clean up all terminal sessions."""
    base_url = "http://localhost:8000"
    
    try:
        # Get all terminals
        response = requests.get(f"{base_url}/api/terminals")
        if response.status_code != 200:
            print(f"Error getting terminals: {response.status_code}")
            return
        
        data = response.json()
        terminals = data.get('data', [])
        
        print(f"Found {len(terminals)} terminal sessions")
        
        # Delete all terminals
        deleted_count = 0
        for terminal in terminals:
            terminal_id = terminal['id']
            print(f"Deleting terminal {terminal_id}...")
            
            try:
                delete_response = requests.delete(f"{base_url}/api/terminals/{terminal_id}")
                if delete_response.status_code == 200:
                    deleted_count += 1
                    print(f"  ✓ Deleted terminal {terminal_id}")
                else:
                    print(f"  ✗ Failed to delete terminal {terminal_id}: {delete_response.status_code}")
            except Exception as e:
                print(f"  ✗ Error deleting terminal {terminal_id}: {e}")
        
        print(f"\nCleanup complete: {deleted_count}/{len(terminals)} terminals deleted")
        
        # Verify cleanup
        verify_response = requests.get(f"{base_url}/api/terminals")
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            remaining = len(verify_data.get('data', []))
            print(f"Remaining terminals: {remaining}")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_terminals() 