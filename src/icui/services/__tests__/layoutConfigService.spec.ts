import { describe, expect, it } from 'vitest';
import { LayoutConfigService } from '../layoutConfigService';

describe('LayoutConfigService', () => {
  it('parses and validates a minimal layout yaml', () => {
    const svc = new LayoutConfigService();
    const yaml = `
name: "Test"
id: "test"
version: 1
layoutMode: h-layout
areas:
  center:
    name: Center
    panelIds: [editor]
    activePanelId: editor
`;

    const res = svc.loadFromYaml(yaml);
    expect(res.ok).toBe(true);
    expect(res.layout?.name).toBe('Test');
    expect(res.layout?.areas.center.panelIds).toEqual(['editor']);
  });

  it('sanitizes invalid activePanelId', () => {
    const svc = new LayoutConfigService();
    const yaml = `
name: "Test"
id: "test"
version: 1
layoutMode: h-layout
areas:
  center:
    name: Center
    panelIds: [editor]
    activePanelId: terminal
`;

    const res = svc.loadFromYaml(yaml);
    expect(res.ok).toBe(true);
    expect(res.layout?.areas.center.activePanelId).toBe('editor');
  });

  it('roundtrips yaml without throwing', () => {
    const svc = new LayoutConfigService();
    const yaml = `
name: "Test"
id: "test"
version: 1
layoutMode: standard
areas:
  left:
    name: Left
    panelIds: [explorer]
`;

    const res = svc.loadFromYaml(yaml);
    expect(res.ok).toBe(true);

    const out = svc.toYaml(res.layout!);
    const res2 = svc.loadFromYaml(out);
    expect(res2.ok).toBe(true);
    expect(res2.layout?.id).toBe('test');
  });

  it('normalizes version to current schema version on load', () => {
    const svc = new LayoutConfigService();
    const yaml = `
name: "Test"
id: "test"
# Intentionally omit or use an older version
version: 0
deviceTarget: desktop
layoutMode: standard
areas:
  center:
    name: Center
    panelIds: [editor]
`;

    const res = svc.loadFromYaml(yaml);
    expect(res.ok).toBe(true);
    expect(res.layout?.version).toBe(1);
    expect(res.layout?.deviceTarget).toBe('desktop');
  });

  it('sanitizes splitConfig fields and keeps numeric values', () => {
    const svc = new LayoutConfigService();
    const yaml = `
name: "Split Test"
id: "split-test"
version: 1
layoutMode: standard
areas:
  center:
    name: Center
    panelIds: [editor]
splitConfig:
  mainVerticalSplit: 65.44
  mainHorizontalSplit: 25
  rightVerticalSplit: 75
  centerVerticalSplit: 70
`;

    const res = svc.loadFromYaml(yaml);
    expect(res.ok).toBe(true);
    expect(res.layout?.splitConfig?.mainVerticalSplit).toBeCloseTo(65.44);
    expect(res.layout?.splitConfig?.mainHorizontalSplit).toBe(25);
    expect(res.layout?.splitConfig?.rightVerticalSplit).toBe(75);
    expect(res.layout?.splitConfig?.centerVerticalSplit).toBe(70);
  });

  it('parses panels list and drops invalid panel entries', () => {
    const svc = new LayoutConfigService();
    const yaml = `
name: "Panels Test"
id: "panels-test"
version: 1
layoutMode: standard
panels:
  - { id: explorer, type: explorer, title: "Explorer" }
  - { id: editor, type: editor }
  - { id: 123, type: nope }
  - { foo: bar }
areas:
  left:
    name: Left
    panelIds: [explorer]
  center:
    name: Center
    panelIds: [editor]
`;

    const res = svc.loadFromYaml(yaml);
    expect(res.ok).toBe(true);
    expect(res.layout?.panels?.map((p) => p.id)).toEqual(['explorer', 'editor']);
  });
});
