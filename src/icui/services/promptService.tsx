/**
 * Prompt Dialog Service
 *
 * Themed, promise-based input dialog for ICUI.
 * Replaces window.prompt with a consistent UI.
 */

import React from 'react';
import { randomId } from '../../icui/lib/id';

export interface PromptOptions {
  title?: string;
  message?: string; // Label/body text
  placeholder?: string;
  initialValue?: string;
  multiline?: boolean;
  password?: boolean; // when true, render input as password type
  confirmText?: string;
  cancelText?: string;
  validate?: (value: string) => string | null; // return string error or null when valid
}

export interface PromptRequest {
  id: string;
  options: Required<Pick<PromptOptions, 'confirmText' | 'cancelText'>> & PromptOptions;
  resolve: (value: string | null) => void;
}

class PromptService {
  private current: PromptRequest | null = null;
  private listeners: Set<(req: PromptRequest | null) => void> = new Set();
  private queue: Array<{ id: string; options: PromptRequest['options']; resolve: (v: string | null) => void }>
    = [];

  prompt(options: PromptOptions): Promise<string | null> {
    const id = randomId('prompt');
    const merged: PromptRequest['options'] = {
      confirmText: options.confirmText ?? 'OK',
      cancelText: options.cancelText ?? 'Cancel',
      ...options,
    };
    return new Promise(resolve => {
      if (this.current) {
        this.queue.push({ id, options: merged, resolve });
      } else {
        this.current = { id, options: merged, resolve };
        this.emit();
      }
    });
  }

  resolve(value: string | null): void {
    if (!this.current) return;
    const { resolve } = this.current;
    try {
      resolve(value);
    } finally {
      const next = this.queue.shift();
      this.current = next ? { id: next.id, options: next.options, resolve: next.resolve } : null;
      this.emit();
    }
  }

  getCurrent(): PromptRequest | null { return this.current; }

  subscribe(cb: (req: PromptRequest | null) => void): () => void {
    this.listeners.add(cb);
    cb(this.current);
    return () => this.listeners.delete(cb);
  }

  private emit(): void { const snap = this.current; this.listeners.forEach(l => l(snap)); }
}

export const promptService = new PromptService();

export const usePromptRequest = () => {
  const [req, setReq] = React.useState<PromptRequest | null>(promptService.getCurrent());
  React.useEffect(() => promptService.subscribe(setReq), []);
  return req;
};

export default promptService;
