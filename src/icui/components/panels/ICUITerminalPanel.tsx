/**
 * ICUI Terminal Panel - Specialized panel for terminal functionality
 * Extends BasePanel with terminal-specific features
 * Part of Phase 4: Specialized Panel Implementations
 */

import React, { useRef, useCallback } from 'react';
import { ICUIBasePanel } from '../ICUIBasePanel';
import type { ICUIBasePanelProps, ICUIPanelInstance } from '../../types/icui-panel';
import XTerminal, { XTerminalRef } from '../../../components/XTerminal';
import { Square, RotateCcw } from 'lucide-react';

export interface ICUITerminalPanelProps extends Omit<ICUIBasePanelProps, 'children'> {
  /** Panel children are not needed as terminal provides its own content */
  children?: React.ReactNode;
  /** Overall theme */
  theme?: 'light' | 'dark';
  /** Terminal-specific options */
  terminalOptions?: {
    /** Whether to auto-connect to websocket on mount */
    autoConnect?: boolean;
    /** Terminal theme preference */
    terminalTheme?: 'light' | 'dark';
    /** Show connection status */
    showStatus?: boolean;
  };
}

/**
 * Terminal Panel Component
 * Provides a dockable terminal interface with WebSocket connectivity
 */
export const ICUITerminalPanel: React.FC<ICUITerminalPanelProps> = ({
  panel,
  theme = 'dark',
  terminalOptions,
  ...basePanelProps
}) => {
  const terminalRef = useRef<XTerminalRef>({} as XTerminalRef);

  // Handle terminal resize when panel resizes
  const handlePanelResize = useCallback(() => {
    // Add a small delay to allow the panel to resize before fitting the terminal
    setTimeout(() => {
      if (terminalRef.current) {
        terminalRef.current.fit();
      }
    }, 50);
  }, []);

  // Handle terminal clear
  const handleTerminalClear = useCallback(() => {
    // Terminal clear is handled internally by XTerminal
    console.log('Terminal cleared');
  }, []);

  return (
    <ICUIBasePanel
      {...basePanelProps}
      panel={panel}
      // Add terminal-specific header props if needed
      headerProps={{
        ...basePanelProps.headerProps,
        // Could add terminal-specific header actions here
      }}
    >
      <div className="flex flex-col h-full">
        <XTerminal
          ref={terminalRef}
          theme={terminalOptions?.terminalTheme ?? theme}
          onClear={handleTerminalClear}
          onResize={handlePanelResize}
          className="flex-1"
        />
      </div>
    </ICUIBasePanel>
  );
};

export default ICUITerminalPanel;
