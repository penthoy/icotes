import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, cleanup, within } from '@testing-library/react';
import ICUITabContainer, { ICUITab } from '../../icui/components/ICUITabContainer';

describe('ICUITabContainer: additional functionality', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  const tabs: ICUITab[] = [
    { id: 'tab1', title: 'First Tab', content: <div data-testid="content-1">First Content</div> },
    { id: 'tab2', title: 'Second Tab', content: <div data-testid="content-2">Second Content</div> },
    { id: 'tab3', title: 'Third Tab', content: <div data-testid="content-3">Third Content</div> },
  ];

  it('renders all tab titles', () => {
    const { getByText } = render(
      <ICUITabContainer tabs={tabs} activeTabId="tab1" onTabActivate={vi.fn()} />
    );

    expect(getByText('First Tab')).toBeInTheDocument();
    expect(getByText('Second Tab')).toBeInTheDocument();
    expect(getByText('Third Tab')).toBeInTheDocument();
  });

  it('shows content for active tab', () => {
    const { getByTestId } = render(
      <ICUITabContainer tabs={tabs} activeTabId="tab2" onTabActivate={vi.fn()} />
    );

    const activeContent = getByTestId('content-2');
    const inactiveContent1 = getByTestId('content-1');
    const inactiveContent3 = getByTestId('content-3');

    // All content should be in DOM but only active should be visible
    expect(activeContent).toBeInTheDocument();
    expect(inactiveContent1).toBeInTheDocument();
    expect(inactiveContent3).toBeInTheDocument();
    
    // Active content should be visible (display: block)
    expect(activeContent).toBeVisible();
    // Inactive content should be hidden (display: none)
    expect(inactiveContent1).not.toBeVisible();
    expect(inactiveContent3).not.toBeVisible();
  });

  it('applies active styles to current tab', () => {
    const { getByTestId } = render(
      <ICUITabContainer tabs={tabs} activeTabId="tab2" onTabActivate={vi.fn()} />
    );

    const tabBar = getByTestId('icui-tab-bar');
    const activeTab = within(tabBar).getByText('Second Tab').closest('div');
    const inactiveTab = within(tabBar).getByText('First Tab').closest('div');

    // Active tab should have border-bottom styling
    expect(activeTab).toHaveClass('border-b-2');
    // Inactive tab should not have border-bottom styling
    expect(inactiveTab).not.toHaveClass('border-b-2');
  });

  it('handles empty tabs array', () => {
    const { container } = render(
      <ICUITabContainer tabs={[]} activeTabId="" onTabActivate={vi.fn()} />
    );

    expect(container.firstChild).toBeInTheDocument();
  });

  it('handles missing active tab gracefully', () => {
    const { getByTestId } = render(
      <ICUITabContainer tabs={tabs} activeTabId="nonexistent" onTabActivate={vi.fn()} />
    );

    // All tab content should be in DOM but none should be visible since activeTabId doesn't match
    const content1 = getByTestId('content-1');
    const content2 = getByTestId('content-2');
    const content3 = getByTestId('content-3');
    
    expect(content1).toBeInTheDocument();
    expect(content2).toBeInTheDocument();
    expect(content3).toBeInTheDocument();
    
    // None should be visible since activeTabId doesn't match any tab
    expect(content1).not.toBeVisible();
    expect(content2).not.toBeVisible();
    expect(content3).not.toBeVisible();
  });

  it('supports className prop', () => {
    const { container } = render(
      <ICUITabContainer 
        tabs={tabs} 
        activeTabId="tab1" 
        onTabActivate={vi.fn()} 
        className="custom-class"
      />
    );

    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('passes through additional props', () => {
    const { container } = render(
      <ICUITabContainer 
        tabs={tabs} 
        activeTabId="tab1" 
        onTabActivate={vi.fn()}
        className="custom-test-class"
      />
    );

    // Check that the component accepts and applies the className prop
    expect(container.firstChild).toHaveClass('custom-test-class');
  });

  it('switches content when activeTabId changes', () => {
    const { getByTestId, rerender } = render(
      <ICUITabContainer tabs={tabs} activeTabId="tab1" onTabActivate={vi.fn()} />
    );

    // Initially, tab1 content should be visible
    expect(getByTestId('content-1')).toBeVisible();
    expect(getByTestId('content-2')).not.toBeVisible();

    // Change active tab via props
    rerender(
      <ICUITabContainer tabs={tabs} activeTabId="tab2" onTabActivate={vi.fn()} />
    );

    // Now tab2 content should be visible
    expect(getByTestId('content-1')).not.toBeVisible();
    expect(getByTestId('content-2')).toBeVisible();
  });

  it('calls onTabActivate with correct tab id on click', () => {
    const onTabActivate = vi.fn();
    const { getByTestId } = render(
      <ICUITabContainer tabs={tabs} activeTabId="tab1" onTabActivate={onTabActivate} />
    );

    const tabBar = getByTestId('icui-tab-bar');
    fireEvent.click(within(tabBar).getByText('Third Tab'));

    // Advance past debounce delay
    vi.advanceTimersByTime(150);

    expect(onTabActivate).toHaveBeenCalledWith('tab3');
  });

  it('does not call onTabActivate when clicking already active tab', () => {
    const onTabActivate = vi.fn();
    const { getByTestId } = render(
      <ICUITabContainer tabs={tabs} activeTabId="tab1" onTabActivate={onTabActivate} />
    );

    const tabBar = getByTestId('icui-tab-bar');
    fireEvent.click(within(tabBar).getByText('First Tab'));

    vi.advanceTimersByTime(150);

    expect(onTabActivate).not.toHaveBeenCalled();
  });
});