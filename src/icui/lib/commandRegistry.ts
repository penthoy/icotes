/**
 * ICUI Command Registry
 * 
 * Centralized command registry for keyboard shortcuts and menu actions.
 * Provides command registration, execution, and keyboard shortcut handling.
 */

import { debugLogger } from '../utils/debugLogger';

export interface Command {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  category?: string;
  shortcut?: string;
  enabled?: boolean;
  visible?: boolean;
  handler: (context?: any) => void | Promise<void>;
}

export interface CommandContext {
  activeElement?: Element;
  selection?: any;
  workspace?: any;
  [key: string]: any;
}

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
  commandId: string;
}

export class CommandRegistry {
  private commands: Map<string, Command> = new Map();
  private shortcuts: Map<string, KeyboardShortcut> = new Map();
  private listeners: Set<(event: CommandEvent) => void> = new Set();
  private context: CommandContext = {};

  /**
   * Register a command
   */
  register(command: Command): void {
    const existing = this.commands.get(command.id);
    
    // Skip duplicate registration to prevent excessive re-registrations
    // This commonly happens during component re-mounts or drag operations
    if (existing) {
      // Log duplicate attempt for debugging
      debugLogger.commandRegistry('duplicate-attempt', command.id, { 
        label: command.label,
        shortcut: command.shortcut 
      });
      
      // Only log in development mode to avoid console spam
      if (process.env.NODE_ENV === 'development') {
        console.debug(`CommandRegistry: Skipping duplicate registration of command '${command.id}'`);
      }
      return;
    }

    // Log successful registration
    debugLogger.commandRegistry('register', command.id, { 
      label: command.label,
      category: command.category,
      shortcut: command.shortcut 
    });

    this.commands.set(command.id, { ...command });
    
    // Register keyboard shortcut if provided
    if (command.shortcut) {
      this.registerShortcut({
        ...this.parseShortcut(command.shortcut),
        commandId: command.id,
      });
    }

    this.notifyListeners({
      type: 'command-registered',
      commandId: command.id,
      command,
    });
  }

  /**
   * Unregister a command
   */
  unregister(commandId: string): void {
    const command = this.commands.get(commandId);
    if (!command) return;

    this.commands.delete(commandId);
    
    // Remove associated shortcuts
    const shortcutKeys = Array.from(this.shortcuts.keys()).filter(
      key => this.shortcuts.get(key)?.commandId === commandId
    );
    shortcutKeys.forEach(key => this.shortcuts.delete(key));

    this.notifyListeners({
      type: 'command-unregistered',
      commandId,
      command,
    });
  }

  /**
   * Execute a command by ID
   */
  async execute(commandId: string, context?: CommandContext): Promise<void> {
    const command = this.commands.get(commandId);
    if (!command) {
      throw new Error(`Command not found: ${commandId}`);
    }

    if (command.enabled === false) {
      throw new Error(`Command disabled: ${commandId}`);
    }

    const mergedContext = { ...this.context, ...context };

    // Log command execution start
    debugLogger.startPerformanceMark(`command-execute-${commandId}`);
    debugLogger.commandRegistry('execute', commandId, { label: command.label });

    this.notifyListeners({
      type: 'command-executing',
      commandId,
      command,
      context: mergedContext,
    });

    try {
      await command.handler(mergedContext);
      
      // Log command execution end
      const duration = debugLogger.endPerformanceMark(`command-execute-${commandId}`, 'CommandRegistry');
      debugLogger.commandRegistry('executed', commandId, { 
        label: command.label,
        duration: duration ? `${duration.toFixed(2)}ms` : 'unknown'
      });
      
      this.notifyListeners({
        type: 'command-executed',
        commandId,
        command,
        context: mergedContext,
      });
    } catch (error) {
      debugLogger.commandRegistry('error', commandId, { 
        label: command.label,
        error: error instanceof Error ? error.message : String(error)
      });
      
      this.notifyListeners({
        type: 'command-error',
        commandId,
        command,
        context: mergedContext,
        error: error instanceof Error ? error : new Error(String(error)),
      });
      throw error;
    }
  }

  /**
   * Get a command by ID
   */
  getCommand(commandId: string): Command | undefined {
    return this.commands.get(commandId);
  }

  /**
   * Get all commands
   */
  getAllCommands(): Command[] {
    return Array.from(this.commands.values());
  }

  /**
   * Get commands by category
   */
  getCommandsByCategory(category: string): Command[] {
    return Array.from(this.commands.values()).filter(
      cmd => cmd.category === category
    );
  }

  /**
   * Register a keyboard shortcut
   */
  registerShortcut(shortcut: KeyboardShortcut): void {
    const key = this.shortcutToKey(shortcut);
    this.shortcuts.set(key, shortcut);
  }

  /**
   * Handle keyboard events
   */
  handleKeydown(event: KeyboardEvent): boolean {
    const shortcut: KeyboardShortcut = {
      key: event.key,
      ctrlKey: event.ctrlKey,
      shiftKey: event.shiftKey,
      altKey: event.altKey,
      metaKey: event.metaKey,
      commandId: '', // Will be filled from registry
    };

    const key = this.shortcutToKey(shortcut);
    const registeredShortcut = this.shortcuts.get(key);

    if (registeredShortcut) {
      event.preventDefault();
      event.stopPropagation();
      
      this.execute(registeredShortcut.commandId).catch(error => {
        console.error('Error executing keyboard shortcut:', error);
      });
      
      return true;
    }

    return false;
  }

  /**
   * Update command context
   */
  updateContext(context: Partial<CommandContext>): void {
    this.context = { ...this.context, ...context };
  }

  /**
   * Get current context
   */
  getContext(): CommandContext {
    return { ...this.context };
  }

  /**
   * Enable/disable a command
   */
  setCommandEnabled(commandId: string, enabled: boolean): void {
    const command = this.commands.get(commandId);
    if (command) {
      command.enabled = enabled;
      this.notifyListeners({
        type: 'command-updated',
        commandId,
        command,
      });
    }
  }

  /**
   * Show/hide a command
   */
  setCommandVisible(commandId: string, visible: boolean): void {
    const command = this.commands.get(commandId);
    if (command) {
      command.visible = visible;
      this.notifyListeners({
        type: 'command-updated',
        commandId,
        command,
      });
    }
  }

  /**
   * Subscribe to command events
   */
  subscribe(listener: (event: CommandEvent) => void): () => void {
    this.listeners.add(listener);
    
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Parse shortcut string into keyboard shortcut object
   */
  private parseShortcut(shortcut: string): Omit<KeyboardShortcut, 'commandId'> {
    const parts = shortcut.toLowerCase().split('+');
    const result: Omit<KeyboardShortcut, 'commandId'> = {
      key: '',
      ctrlKey: false,
      shiftKey: false,
      altKey: false,
      metaKey: false,
    };

    parts.forEach(part => {
      switch (part.trim()) {
        case 'ctrl':
        case 'control':
          result.ctrlKey = true;
          break;
        case 'shift':
          result.shiftKey = true;
          break;
        case 'alt':
          result.altKey = true;
          break;
        case 'meta':
        case 'cmd':
        case 'command':
          result.metaKey = true;
          break;
        default:
          result.key = part.trim();
          break;
      }
    });

    return result;
  }

  /**
   * Convert shortcut to unique key string
   */
  private shortcutToKey(shortcut: Omit<KeyboardShortcut, 'commandId'>): string {
    const modifiers = [];
    if (shortcut.ctrlKey) modifiers.push('ctrl');
    if (shortcut.shiftKey) modifiers.push('shift');
    if (shortcut.altKey) modifiers.push('alt');
    if (shortcut.metaKey) modifiers.push('meta');
    
    return [...modifiers, shortcut.key.toLowerCase()].join('+');
  }

  /**
   * Notify listeners of command events
   */
  private notifyListeners(event: CommandEvent): void {
    this.listeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error('Error in command event listener:', error);
      }
    });
  }
}

/**
 * Command event types
 */
export type CommandEvent = 
  | { type: 'command-registered'; commandId: string; command: Command }
  | { type: 'command-unregistered'; commandId: string; command: Command }
  | { type: 'command-updated'; commandId: string; command: Command }
  | { type: 'command-executing'; commandId: string; command: Command; context: CommandContext }
  | { type: 'command-executed'; commandId: string; command: Command; context: CommandContext }
  | { type: 'command-error'; commandId: string; command: Command; context: CommandContext; error: Error };

/**
 * Built-in command categories
 */
export const CommandCategories = {
  FILE: 'file',
  EDIT: 'edit',
  VIEW: 'view',
  NAVIGATION: 'navigation',
  TERMINAL: 'terminal',
  DEBUG: 'debug',
  HELP: 'help',
  CUSTOM: 'custom',
} as const;

/**
 * Command utilities
 */
export class CommandUtils {
  /**
   * Create a simple command
   */
  static create(
    id: string,
    label: string,
    handler: (context?: any) => void | Promise<void>,
    options: Partial<Omit<Command, 'id' | 'label' | 'handler'>> = {}
  ): Command {
    return {
      id,
      label,
      handler,
      enabled: true,
      visible: true,
      ...options,
    };
  }

  /**
   * Create a command with keyboard shortcut
   */
  static createWithShortcut(
    id: string,
    label: string,
    shortcut: string,
    handler: (context?: any) => void | Promise<void>,
    options: Partial<Omit<Command, 'id' | 'label' | 'shortcut' | 'handler'>> = {}
  ): Command {
    return CommandUtils.create(id, label, handler, {
      shortcut,
      ...options,
    });
  }

  /**
   * Validate shortcut string format
   */
  static validateShortcut(shortcut: string): boolean {
    try {
      const parts = shortcut.toLowerCase().split('+');
      return parts.length >= 1 && parts.every(part => 
        ['ctrl', 'control', 'shift', 'alt', 'meta', 'cmd', 'command'].includes(part.trim()) ||
        part.trim().length === 1
      );
    } catch {
      return false;
    }
  }
}

/**
 * Global command registry instance
 */
export const globalCommandRegistry = new CommandRegistry();
