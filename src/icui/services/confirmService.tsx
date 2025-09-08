/**
 * Confirm Dialog Service
 * 
 * Centralized, promise-based confirmation dialog for ICUI.
 * Replaces window.confirm with a themed, accessible modal.
 */

import React from 'react';

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

export interface ConfirmRequest {
  id: string;
  options: Required<Pick<ConfirmOptions, 'message'>> & ConfirmOptions;
  resolve: (value: boolean) => void;
}

class ConfirmService {
  private current: ConfirmRequest | null = null;
  private listeners: Set<(req: ConfirmRequest | null) => void> = new Set();

  /**
   * Show a confirmation dialog and resolve with true/false.
   */
  confirm(options: ConfirmOptions): Promise<boolean> {
    const id = `confirm_${crypto.randomUUID()}`;
    const merged: ConfirmRequest['options'] = {
      message: options.message,
      title: options.title,
      confirmText: options.confirmText ?? 'Confirm',
      cancelText: options.cancelText ?? 'Cancel',
      danger: options.danger ?? false,
    };

    return new Promise<boolean>((resolve) => {
      this.current = { id, options: merged, resolve };
      this.emit();
    });
  }

  /** Resolve the active confirmation with a boolean result */
  resolve(result: boolean): void {
    if (!this.current) return;
    const { resolve } = this.current;
    this.current = null;
    try {
      resolve(result);
    } finally {
      this.emit();
    }
  }

  getCurrent(): ConfirmRequest | null {
    return this.current;
  }

  subscribe(listener: (req: ConfirmRequest | null) => void): () => void {
    this.listeners.add(listener);
    listener(this.current);
    return () => this.listeners.delete(listener);
  }

  private emit(): void {
    const snapshot = this.current;
    this.listeners.forEach((cb) => cb(snapshot));
  }
}

export const confirmService = new ConfirmService();

/**
 * React hook for current confirm request
 */
export const useConfirmRequest = () => {
  const [req, setReq] = React.useState<ConfirmRequest | null>(confirmService.getCurrent());
  React.useEffect(() => confirmService.subscribe(setReq), []);
  return req;
};

export default confirmService;
