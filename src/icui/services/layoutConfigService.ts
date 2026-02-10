import YAML from 'js-yaml';
import type { ICUILayoutArea, ICUILayoutConfig } from '../components/ICUILayout';
import { resolveWorkspacePath } from '../lib/workspaceUtils';

export type LayoutFileId = string;

export interface LayoutConfigValidationResult {
  ok: boolean;
  errors: string[];
  warnings: string[];
  layout?: ICUILayoutConfig;
}

const DEFAULT_SCHEMA_VERSION = 1;
const DEFAULT_LAYOUT_DIR = '/.icotes/layout';

function getDefaultLayoutDir(): string {
  try {
    // Prefer workspace-rooted layout dir for consistent backend file operations.
    return resolveWorkspacePath('.icotes/layout');
  } catch {
    // Fallback to previous relative behavior if workspace root isn't configured.
    return DEFAULT_LAYOUT_DIR;
  }
}

function isPlainObject(value: unknown): value is Record<string, any> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function ensureArrayOfStrings(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v) => typeof v === 'string');
}

function sanitizeArea(areaId: string, area: any): ICUILayoutArea {
  const panelIds = ensureArrayOfStrings(area?.panelIds);
  let activePanelId = typeof area?.activePanelId === 'string' ? area.activePanelId : undefined;

  if (activePanelId && !panelIds.includes(activePanelId)) {
    activePanelId = panelIds[0];
  }

  return {
    id: typeof area?.id === 'string' ? area.id : areaId,
    name: typeof area?.name === 'string' ? area.name : areaId,
    panelIds,
    activePanelId,
    size: typeof area?.size === 'number' ? area.size : undefined,
    visible: typeof area?.visible === 'boolean' ? area.visible : undefined,
    collapsible: typeof area?.collapsible === 'boolean' ? area.collapsible : undefined,
    width: typeof area?.width === 'number' || typeof area?.width === 'string' ? area.width : undefined,
    height: typeof area?.height === 'number' || typeof area?.height === 'string' ? area.height : undefined,
    minWidth: typeof area?.minWidth === 'number' ? area.minWidth : undefined,
    minHeight: typeof area?.minHeight === 'number' ? area.minHeight : undefined,
  };
}

function sanitizeLayoutObject(raw: any): ICUILayoutConfig {
  const areasRaw = isPlainObject(raw?.areas) ? raw.areas : {};
  const sanitizedAreas: Record<string, ICUILayoutArea> = {};

  Object.keys(areasRaw).forEach((areaId) => {
    sanitizedAreas[areaId] = sanitizeArea(areaId, areasRaw[areaId]);
  });

  const panelsRaw = Array.isArray(raw?.panels) ? raw.panels : undefined;
  const panels = panelsRaw
    ? panelsRaw
        .filter((p) => isPlainObject(p) && typeof p.id === 'string' && typeof p.type === 'string')
        .map((p) => ({
          id: p.id,
          type: p.type,
          title: typeof p.title === 'string' ? p.title : undefined,
          icon: typeof p.icon === 'string' ? p.icon : undefined,
          config: isPlainObject(p.config) ? p.config : undefined,
        }))
    : undefined;

  const layoutMode = raw?.layoutMode;

  return {
    name: typeof raw?.name === 'string' ? raw.name : undefined,
    id: typeof raw?.id === 'string' ? raw.id : undefined,
    description: typeof raw?.description === 'string' ? raw.description : undefined,
    version: typeof raw?.version === 'number' ? raw.version : DEFAULT_SCHEMA_VERSION,
    deviceTarget:
      raw?.deviceTarget === 'desktop' || raw?.deviceTarget === 'mobile' || raw?.deviceTarget === 'any'
        ? raw.deviceTarget
        : undefined,
    layoutMode: layoutMode === 'standard' || layoutMode === 'h-layout' || layoutMode === 'mobile' ? layoutMode : undefined,
    panels,
    areas: sanitizedAreas,
    splitConfig: isPlainObject(raw?.splitConfig)
      ? {
          mainVerticalSplit: typeof raw.splitConfig.mainVerticalSplit === 'number' ? raw.splitConfig.mainVerticalSplit : undefined,
          mainHorizontalSplit: typeof raw.splitConfig.mainHorizontalSplit === 'number' ? raw.splitConfig.mainHorizontalSplit : undefined,
          rightVerticalSplit: typeof raw.splitConfig.rightVerticalSplit === 'number' ? raw.splitConfig.rightVerticalSplit : undefined,
          centerVerticalSplit: typeof raw.splitConfig.centerVerticalSplit === 'number' ? raw.splitConfig.centerVerticalSplit : undefined,
        }
      : undefined,
  };
}

function validateLayout(layout: ICUILayoutConfig): LayoutConfigValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!layout.name) errors.push('Missing required field: name');
  if (!layout.id) errors.push('Missing required field: id');

  if (!layout.areas || Object.keys(layout.areas).length === 0) {
    errors.push('Missing required field: areas (must define at least one area)');
  }

  // Validate activePanelId consistency
  Object.keys(layout.areas || {}).forEach((areaId) => {
    const area = layout.areas[areaId];
    if (!area.panelIds || area.panelIds.length === 0) {
      warnings.push(`Area "${areaId}" has no panelIds`);
      return;
    }
    if (area.activePanelId && !area.panelIds.includes(area.activePanelId)) {
      warnings.push(`Area "${areaId}" has activePanelId not in panelIds (will be sanitized)`);
    }
  });

  // If panels list exists, ensure all referenced panelIds exist in panels list
  if (layout.panels && layout.panels.length > 0) {
    const known = new Set(layout.panels.map((p) => p.id));
    Object.keys(layout.areas || {}).forEach((areaId) => {
      const area = layout.areas[areaId];
      area.panelIds.forEach((pid) => {
        if (!known.has(pid)) {
          warnings.push(`Area "${areaId}" references panelId "${pid}" not declared in panels[]`);
        }
      });
    });
  }

  return {
    ok: errors.length === 0,
    errors,
    warnings,
    layout,
  };
}

export class LayoutConfigService {
  readonly layoutDir: string;

  constructor(layoutDir: string = getDefaultLayoutDir()) {
    this.layoutDir = layoutDir;
  }

  loadFromYaml(yamlString: string): LayoutConfigValidationResult {
    try {
      const parsed = YAML.load(yamlString);
      const sanitized = sanitizeLayoutObject(parsed);
      return validateLayout(sanitized);
    } catch (err) {
      return {
        ok: false,
        errors: [err instanceof Error ? err.message : 'Failed to parse YAML'],
        warnings: [],
      };
    }
  }

  toYaml(config: ICUILayoutConfig): string {
    // Serialize a sanitized version to keep output stable and safe.
    const sanitized = sanitizeLayoutObject(config);
    return YAML.dump(sanitized, {
      noRefs: true,
      lineWidth: 120,
      sortKeys: false,
    });
  }

  private async apiGetJson<T>(url: string): Promise<T> {
    const response = await fetch(url, {
      // Prevent stale layout/settings after refresh.
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
        Pragma: 'no-cache',
      },
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`);
    }
    return (await response.json()) as T;
  }

  private async apiPutJson<T>(url: string, body: any): Promise<T> {
    const response = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`);
    }
    return (await response.json()) as T;
  }

  private async apiPostJson<T>(url: string, body: any): Promise<T> {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`);
    }
    return (await response.json()) as T;
  }

  async listLayouts(): Promise<Array<{ name: string; path: string }>> {
    // Uses existing REST endpoint: GET /api/files?path=...
    const result = await this.apiGetJson<any>(`/api/files?path=${encodeURIComponent(this.layoutDir)}&include_hidden=false`);
    const files = Array.isArray(result?.data) ? result.data : [];

    return files
      .filter((f: any) => !f?.is_directory)
      .map((f: any) => ({ name: String(f.name || ''), path: String(f.path || '') }))
      .filter((f: any) => f.name.toLowerCase().endsWith('.yaml') || f.name.toLowerCase().endsWith('.yml'))
      .sort((a: any, b: any) => a.name.localeCompare(b.name));
  }

  async loadFromFile(path: string): Promise<LayoutConfigValidationResult> {
    const result = await this.apiGetJson<any>(`/api/files/content?path=${encodeURIComponent(path)}`);
    const content = result?.data?.content;
    if (typeof content !== 'string') {
      return { ok: false, errors: ['Invalid response: missing content'], warnings: [] };
    }
    return this.loadFromYaml(content);
  }

  async ensureLayoutDirExists(): Promise<void> {
    // Uses existing REST endpoint: POST /api/files to create directory
    await this.apiPostJson(`/api/files`, {
      path: this.layoutDir,
      type: 'directory',
      create_dirs: true,
    });
  }

  async saveToFile(config: ICUILayoutConfig, path: string): Promise<void> {
    const yaml = this.toYaml(config);

    // PUT /api/files updates or creates with create_dirs.
    await this.apiPutJson(`/api/files`, {
      path,
      content: yaml,
      encoding: 'utf-8',
      create_dirs: true,
      type: 'file',
    });
  }
}

export const layoutConfigService = new LayoutConfigService();
