/**
 * ICUI Panel Factory
 * 
 * Instantiate panels by type with configuration.
 * Apply panel-default menu schemas which can be extended/overridden by user config.
 */

import React, { ComponentType } from 'react';
import { PanelType, PanelMetadata, globalPanelRegistry } from './panelRegistry';
import { MenuSchema } from './menuSchemas';

/**
 * Panel configuration options
 */
export interface PanelConfig {
  id?: string;
  title?: string;
  initialData?: any;
  customContextMenu?: MenuSchema;
  overrideDefaultMenu?: boolean;
  customCapabilities?: string[];
  size?: { width?: number | string; height?: number | string };
  position?: { x?: number; y?: number };
  persistent?: boolean;
  closable?: boolean;
  resizable?: boolean;
  draggable?: boolean;
  [key: string]: any;
}

/**
 * Panel instance represents a specific panel with configuration
 */
export interface PanelInstance {
  id: string;
  type: PanelType;
  metadata: PanelMetadata;
  config: PanelConfig;
  contextMenu: MenuSchema;
  component: ComponentType<any>;
  created: Date;
  lastActive: Date;
  state?: any;
}

/**
 * Panel factory manages panel creation and configuration
 */
export class PanelFactory {
  private panelComponents: Map<PanelType, ComponentType<any>> = new Map();
  private instances: Map<string, PanelInstance> = new Map();
  private listeners: Set<(event: PanelFactoryEvent) => void> = new Set();

  /**
   * Register a panel component for a specific panel type
   */
  registerComponent(panelType: PanelType, component: ComponentType<any>): void {
    this.panelComponents.set(panelType, component);
    this.emit({ type: 'component-registered', panelType, component });
  }

  /**
   * Unregister a panel component
   */
  unregisterComponent(panelType: PanelType): boolean {
    const component = this.panelComponents.get(panelType);
    if (!component) return false;

    this.panelComponents.delete(panelType);
    this.emit({ type: 'component-unregistered', panelType, component });
    return true;
  }

  /**
   * Create a new panel instance
   */
  createPanel(panelType: PanelType, config: PanelConfig = {}): PanelInstance | null {
    // Get panel metadata from registry
    const metadata = globalPanelRegistry.getPanel(panelType);
    if (!metadata) {
      console.error(`Panel type not registered: ${panelType}`);
      return null;
    }

    // Get panel component
    const component = this.panelComponents.get(panelType);
    if (!component) {
      console.error(`No component registered for panel type: ${panelType}`);
      return null;
    }

    // Generate unique ID if not provided
    const id = config.id || this.generatePanelId(panelType);

    // Build context menu
    const contextMenu = this.buildContextMenu(metadata, config);

    // Create panel instance
    const instance: PanelInstance = {
      id,
      type: panelType,
      metadata,
      config: {
        persistent: false,
        closable: true,
        resizable: true,
        draggable: true,
        ...config,
      },
      contextMenu,
      component,
      created: new Date(),
      lastActive: new Date(),
      state: config.initialData || {},
    };

    // Store instance
    this.instances.set(id, instance);

    // Emit event
    this.emit({ type: 'panel-created', instance });

    return instance;
  }

  /**
   * Get a panel instance by ID
   */
  getInstance(id: string): PanelInstance | undefined {
    return this.instances.get(id);
  }

  /**
   * Get all panel instances
   */
  getAllInstances(): PanelInstance[] {
    return Array.from(this.instances.values());
  }

  /**
   * Get panel instances by type
   */
  getInstancesByType(panelType: PanelType): PanelInstance[] {
    return this.getAllInstances().filter(instance => instance.type === panelType);
  }

  /**
   * Update panel instance configuration
   */
  updatePanelConfig(id: string, updates: Partial<PanelConfig>): boolean {
    const instance = this.instances.get(id);
    if (!instance) return false;

    // Update configuration
    const updatedConfig = { ...instance.config, ...updates };
    const updatedInstance: PanelInstance = {
      ...instance,
      config: updatedConfig,
      contextMenu: updates.customContextMenu || updates.overrideDefaultMenu !== undefined
        ? this.buildContextMenu(instance.metadata, updatedConfig)
        : instance.contextMenu,
      lastActive: new Date(),
    };

    this.instances.set(id, updatedInstance);
    this.emit({ type: 'panel-updated', instance: updatedInstance });

    return true;
  }

  /**
   * Update panel state
   */
  updatePanelState(id: string, state: any): boolean {
    const instance = this.instances.get(id);
    if (!instance) return false;

    const updatedInstance: PanelInstance = {
      ...instance,
      state: { ...instance.state, ...state },
      lastActive: new Date(),
    };

    this.instances.set(id, updatedInstance);
    this.emit({ type: 'panel-state-updated', instance: updatedInstance });

    return true;
  }

  /**
   * Clone an existing panel instance
   */
  clonePanel(id: string, newConfig: Partial<PanelConfig> = {}): PanelInstance | null {
    const instance = this.instances.get(id);
    if (!instance) return null;

    // Merge config but ensure new ID
    const cloneConfig: PanelConfig = {
      ...instance.config,
      ...newConfig,
      id: newConfig.id || this.generatePanelId(instance.type),
    };

    return this.createPanel(instance.type, cloneConfig);
  }

  /**
   * Destroy a panel instance
   */
  destroyPanel(id: string): boolean {
    const instance = this.instances.get(id);
    if (!instance) return false;

    this.instances.delete(id);
    this.emit({ type: 'panel-destroyed', instance });

    return true;
  }

  /**
   * Mark panel as active (updates lastActive timestamp)
   */
  markPanelActive(id: string): boolean {
    const instance = this.instances.get(id);
    if (!instance) return false;

    const updatedInstance: PanelInstance = {
      ...instance,
      lastActive: new Date(),
    };

    this.instances.set(id, updatedInstance);
    return true;
  }

  /**
   * Get panel statistics
   */
  getStatistics(): {
    totalPanels: number;
    panelsByType: Record<PanelType, number>;
    oldestPanel: Date | null;
    newestPanel: Date | null;
    mostRecentlyActive: Date | null;
  } {
    const instances = this.getAllInstances();
    
    const panelsByType = instances.reduce((acc, instance) => {
      acc[instance.type] = (acc[instance.type] || 0) + 1;
      return acc;
    }, {} as Record<PanelType, number>);

    const dates = instances.map(i => i.created);
    const activeDates = instances.map(i => i.lastActive);

    return {
      totalPanels: instances.length,
      panelsByType,
      oldestPanel: dates.length > 0 ? new Date(Math.min(...dates.map(d => d.getTime()))) : null,
      newestPanel: dates.length > 0 ? new Date(Math.max(...dates.map(d => d.getTime()))) : null,
      mostRecentlyActive: activeDates.length > 0 ? new Date(Math.max(...activeDates.map(d => d.getTime()))) : null,
    };
  }

  /**
   * Subscribe to factory events
   */
  subscribe(listener: (event: PanelFactoryEvent) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Generate unique panel ID
   */
  private generatePanelId(panelType: PanelType): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 6);
    return `${panelType}-${timestamp}-${random}`;
  }

  /**
   * Build context menu for panel, combining default and custom menus
   */
  private buildContextMenu(metadata: PanelMetadata, config: PanelConfig): MenuSchema {
    if (config.overrideDefaultMenu && config.customContextMenu) {
      return config.customContextMenu;
    }

    if (config.customContextMenu) {
      // Merge custom menu with default menu
      return {
        id: `${metadata.defaultContextMenu.id}-custom`,
        items: [
          ...metadata.defaultContextMenu.items,
          { id: 'custom-separator', label: '', separator: true },
          ...config.customContextMenu.items,
        ],
      };
    }

    return metadata.defaultContextMenu;
  }

  private emit(event: PanelFactoryEvent): void {
    this.listeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error('Error in panel factory event listener:', error);
      }
    });
  }
}

/**
 * Panel factory event types
 */
export type PanelFactoryEvent = 
  | { type: 'component-registered'; panelType: PanelType; component: ComponentType<any> }
  | { type: 'component-unregistered'; panelType: PanelType; component: ComponentType<any> }
  | { type: 'panel-created'; instance: PanelInstance }
  | { type: 'panel-updated'; instance: PanelInstance }
  | { type: 'panel-state-updated'; instance: PanelInstance }
  | { type: 'panel-destroyed'; instance: PanelInstance };

/**
 * Panel factory utilities
 */
export class PanelFactoryUtils {
  /**
   * Create a batch of panels from configurations
   */
  static createPanelBatch(
    factory: PanelFactory,
    configs: Array<{ type: PanelType; config: PanelConfig }>
  ): PanelInstance[] {
    const instances: PanelInstance[] = [];
    
    for (const { type, config } of configs) {
      const instance = factory.createPanel(type, config);
      if (instance) {
        instances.push(instance);
      }
    }

    return instances;
  }

  /**
   * Export panel configurations for persistence
   */
  static exportPanelConfigs(factory: PanelFactory): Array<{ type: PanelType; config: PanelConfig }> {
    return factory.getAllInstances()
      .filter(instance => instance.config.persistent)
      .map(instance => ({
        type: instance.type,
        config: instance.config,
      }));
  }

  /**
   * Import panel configurations from persistence
   */
  static importPanelConfigs(
    factory: PanelFactory,
    configs: Array<{ type: PanelType; config: PanelConfig }>
  ): PanelInstance[] {
    return PanelFactoryUtils.createPanelBatch(factory, configs);
  }

  /**
   * Get panels suitable for specific layout positions
   */
  static getPanelsForPosition(
    factory: PanelFactory,
    position: 'left' | 'right' | 'top' | 'bottom' | 'center'
  ): PanelInstance[] {
    return factory.getAllInstances().filter(instance => 
      instance.metadata.defaultPosition === position
    );
  }

  /**
   * Create default workspace layout
   */
  static createDefaultWorkspace(factory: PanelFactory): {
    left: PanelInstance[];
    center: PanelInstance[];
    right: PanelInstance[];
    bottom: PanelInstance[];
  } {
    const explorer = factory.createPanel('explorer', { 
      id: 'default-explorer',
      persistent: true 
    });
    
    const editor = factory.createPanel('editor', { 
      id: 'default-editor',
      persistent: true 
    });
    
    const terminal = factory.createPanel('terminal', { 
      id: 'default-terminal',
      persistent: true 
    });
    
    const chat = factory.createPanel('chat', { 
      id: 'default-chat',
      persistent: true 
    });

    return {
      left: explorer ? [explorer] : [],
      center: editor ? [editor] : [],
      right: chat ? [chat] : [],
      bottom: terminal ? [terminal] : [],
    };
  }
}

/**
 * Global panel factory instance
 */
export const globalPanelFactory = new PanelFactory();

export default PanelFactory;
