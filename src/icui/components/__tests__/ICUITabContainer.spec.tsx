import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, cleanup, within } from '@testing-library/react';
import ICUITabContainer, { ICUITab } from '../ICUITabContainer';

describe('ICUITabContainer: debounce and circuit breaker', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  const tabs: ICUITab[] = [
    { id: 'a', title: 'A', content: <div>A</div> },
    { id: 'b', title: 'B', content: <div>B</div> },
    { id: 'c', title: 'C', content: <div>C</div> },
  ];

  it('debounces activation to the last clicked tab within 100ms', () => {
    const onActivate = vi.fn();
  const { getByTestId, getByText } = render(
      <ICUITabContainer tabs={tabs} activeTabId={'a'} onTabActivate={onActivate} />
    );

  const bar = getByTestId('icui-tab-bar');
  fireEvent.click(within(bar).getByText('B'));
  fireEvent.click(within(bar).getByText('C'));

    // advance less than debounce window
    vi.advanceTimersByTime(90);
    expect(onActivate).not.toHaveBeenCalled();

    // after 100ms, only last should fire
    vi.advanceTimersByTime(20);
    expect(onActivate).toHaveBeenCalledTimes(1);
    expect(onActivate).toHaveBeenCalledWith('c');
  });

  it('applies soft circuit breaker after many rapid switches', () => {
    const onActivate = vi.fn();
  const { getByTestId } = render(
      <ICUITabContainer tabs={tabs} activeTabId={'a'} onTabActivate={onActivate} />
    );

    // 7 rapid clicks within 1s should trigger breaker and reduce calls
  const bar = getByTestId('icui-tab-bar');
  fireEvent.click(within(bar).getByText('B'));
    vi.advanceTimersByTime(10);
  fireEvent.click(within(bar).getByText('A'));
    vi.advanceTimersByTime(10);
  fireEvent.click(within(bar).getByText('B'));
    vi.advanceTimersByTime(10);
  fireEvent.click(within(bar).getByText('A'));
    vi.advanceTimersByTime(10);
  fireEvent.click(within(bar).getByText('B'));
    vi.advanceTimersByTime(10);
  fireEvent.click(within(bar).getByText('A'));
    vi.advanceTimersByTime(10);
  fireEvent.click(within(bar).getByText('B'));

    // Run timers to flush debounces
    vi.advanceTimersByTime(200);

    // Should not call for every click; at least 1, less than 7
    expect(onActivate.mock.calls.length).toBeGreaterThan(0);
    expect(onActivate.mock.calls.length).toBeLessThan(7);
  });
});
