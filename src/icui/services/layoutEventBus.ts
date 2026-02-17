/**
 * Layout Event Bus
 * Centralized event-driven layout mutation system for decoupling
 * mutation sources (menu, agent, shortcuts) from the layout state owner
 */

import EventEmitter from 'eventemitter3';
import type { ICUILayoutConfig } from '../components/ICUILayout';

export interface LayoutEventMap {
  'layout:update': [Partial<ICUILayoutConfig>];
  'layout:switch': [string]; // layout name/id
  'layout:panel:activate': [{ areaId: string; panelId: string }];
  'layout:panel:add': [{ panelType: string; areaId: string; index?: number }];
  'layout:panel:remove': [{ panelId: string }];
  'layout:panel:move': [{ panelId: string; fromAreaId: string; toAreaId: string; index?: number }];
  'layout:area:resize': [{ areaId: string; size: number }];
  'layout:area:toggle': [{ areaId: string; visible: boolean }];
  'layout:split:update': [{ splitKey: string; percentage: number }];
}

class LayoutEventBus extends EventEmitter<LayoutEventMap> {
  private static instance: LayoutEventBus | null = null;

  private constructor() {
    super();
  }

  static getInstance(): LayoutEventBus {
    if (!LayoutEventBus.instance) {
      LayoutEventBus.instance = new LayoutEventBus();
    }
    return LayoutEventBus.instance;
  }

  // Typed emit helpers for better DX
  emitLayoutUpdate(partialConfig: Partial<ICUILayoutConfig>) {
    this.emit('layout:update', partialConfig);
  }

  emitLayoutSwitch(layoutId: string) {
    this.emit('layout:switch', layoutId);
  }

  emitPanelActivate(areaId: string, panelId: string) {
    this.emit('layout:panel:activate', { areaId, panelId });
  }

  emitPanelAdd(panelType: string, areaId: string, index?: number) {
    this.emit('layout:panel:add', { panelType, areaId, index });
  }

  emitPanelRemove(panelId: string) {
    this.emit('layout:panel:remove', { panelId });
  }

  emitPanelMove(panelId: string, fromAreaId: string, toAreaId: string, index?: number) {
    this.emit('layout:panel:move', { panelId, fromAreaId, toAreaId, index });
  }

  emitAreaResize(areaId: string, size: number) {
    this.emit('layout:area:resize', { areaId, size });
  }

  emitAreaToggle(areaId: string, visible: boolean) {
    this.emit('layout:area:toggle', { areaId, visible });
  }

  emitSplitUpdate(splitKey: string, percentage: number) {
    this.emit('layout:split:update', { splitKey, percentage });
  }
}

export const layoutEventBus = LayoutEventBus.getInstance();
