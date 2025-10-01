import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import React from 'react';
import JumpToLatestButton from '../../icui/components/chat/widgets/JumpToLatestButton';

describe('JumpToLatestButton component', () => {
  it('renders with correct text', () => {
    const mockOnClick = vi.fn();
    const { getByText } = render(<JumpToLatestButton onClick={mockOnClick} />);
    
    expect(getByText('Jump to latest')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const mockOnClick = vi.fn();
    const { getByText } = render(<JumpToLatestButton onClick={mockOnClick} />);
    
    const button = getByText('Jump to latest');
    fireEvent.click(button);
    
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('has proper styling classes', () => {
    const mockOnClick = vi.fn();
    const { getByText } = render(<JumpToLatestButton onClick={mockOnClick} />);
    
    const button = getByText('Jump to latest');
    
    expect(button).toHaveClass('px-3', 'py-1.5', 'text-xs', 'rounded-full', 'shadow', 'border');
  });

  it('is wrapped in sticky positioned container', () => {
    const mockOnClick = vi.fn();
    const { container } = render(<JumpToLatestButton onClick={mockOnClick} />);
    
    const stickyContainer = container.querySelector('.sticky');
    expect(stickyContainer).toBeInTheDocument();
    expect(stickyContainer).toHaveClass('bottom-2', 'flex', 'justify-center', 'z-10');
  });
});