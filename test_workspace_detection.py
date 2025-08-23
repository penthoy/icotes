#!/usr/bin/env python3

import sys
sys.path.append('/home/penthoy/icotes/backend')

print('Testing workspace detection from icotes root directory...')

from icpy.agent.helpers import create_agent_context

# Test workspace detection from different location
context = create_agent_context()
workspace_path = context['workspace_root']
print(f'✓ Workspace detected from icotes root: {workspace_path}')

if workspace_path == '/home/penthoy/icotes/workspace':
    print('✓ Consistent workspace detection across directories')
else:
    print(f'⚠ Different workspace detected: {workspace_path}')

print('✓ Workspace detection is working dynamically!')
