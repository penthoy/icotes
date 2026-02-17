import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResetLayoutDialog } from '../ResetLayoutDialog';

describe('ResetLayoutDialog', () => {
  it('renders nothing when closed', () => {
    render(
      <ResetLayoutDialog
        open={false}
        onOpenChange={() => {}}
        onConfirm={() => {}}
      />
    );

    expect(screen.queryByText('Reset Layout?')).not.toBeInTheDocument();
  });

  it('calls onOpenChange(false) when clicking Cancel', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();

    render(
      <ResetLayoutDialog
        open={true}
        onOpenChange={onOpenChange}
        onConfirm={() => {}}
      />
    );

    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('calls onConfirm and closes when clicking Reset Layout', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const onConfirm = vi.fn();

    render(
      <ResetLayoutDialog
        open={true}
        onOpenChange={onOpenChange}
        onConfirm={onConfirm}
        layoutName="H Layout"
      />
    );

    await user.click(screen.getByRole('button', { name: 'Reset Layout' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('closes when clicking backdrop', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();

    const { container } = render(
      <ResetLayoutDialog
        open={true}
        onOpenChange={onOpenChange}
        onConfirm={() => {}}
      />
    );

    // Backdrop is the first div we render
    const backdrop = container.firstElementChild as HTMLElement;
    await user.click(backdrop);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
