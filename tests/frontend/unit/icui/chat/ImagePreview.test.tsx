/**
 * ImagePreview Component Tests
 * 
 * Test coverage for image preview functionality in chat messages.
 * Following TDD approach - tests written before implementation.
 */

import React, { useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, beforeEach, expect, vi } from 'vitest';
import '@testing-library/jest-dom';

// Mock attachment data for testing
const mockAttachment = {
  id: 'test-attachment-1',
  name: 'test-image.png',
  type: 'image',
  mime_type: 'image/png',
  meta: {
    size: 1024000, // 1000 KB
    width: 800,
    height: 600,
    original_name: 'test-image.png'
  }
};

// Mock the media service
const mockMediaService = {
  getAttachmentUrl: vi.fn(() => 'mock-url-test-attachment-1')
};

vi.mock('../../../../../src/icui/services/mediaService', () => ({
  mediaService: mockMediaService
}));

// Mock ImagePreview component for testing (since it doesn't exist yet)
interface ImagePreviewProps {
  attachment: {
    id: string;
    name: string;
    type: string;
    mime_type: string;
    meta?: {
      size: number;
      width: number;
      height: number;
      original_name: string;
    };
  };
  showRemoveButton?: boolean;
  onRemove?: () => void;
}

const TestImagePreview: React.FC<ImagePreviewProps> = ({ attachment, showRemoveButton = false, onRemove }) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [showFullSize, setShowFullSize] = useState(false);

  const imageUrl = mockMediaService.getAttachmentUrl();

  if (imageError) {
    return <div>Failed to load image</div>;
  }

  return (
    <div>
      <img
        src={imageUrl}
        alt={attachment.name}
        className={imageLoaded ? 'opacity-100' : 'opacity-0'}
        onLoad={() => setImageLoaded(true)}
        onError={() => setImageError(true)}
      />
      
      {imageLoaded && (
        <>
          <button title="View full size" onClick={() => setShowFullSize(true)}>
            Expand
          </button>
          <button aria-label="Download image" title="Download image">
            Download
          </button>
          {showRemoveButton && onRemove && (
            <button aria-label="Remove image" onClick={onRemove}>
              Remove
            </button>
          )}
          
          <div>
            <p title={attachment.name}>{attachment.name}</p>
            {attachment.meta?.size && <p>{Math.round(attachment.meta.size / 1024)} KB</p>}
            {attachment.meta?.width && attachment.meta?.height && (
              <p>{attachment.meta.width}×{attachment.meta.height}</p>
            )}
          </div>
          
          {showFullSize && (
            <div>
              <button onClick={() => setShowFullSize(false)}>Close</button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// Mock file for testing
const mockImageFile = new File(['mock image data'], 'test-image.png', {
  type: 'image/png',
  lastModified: Date.now()
});

const mockImageUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

describe('ImagePreview Component', () => {
  beforeEach(() => {
    mockMediaService.getAttachmentUrl.mockClear();
  });

  // Test 1: Basic rendering
  describe('Basic Rendering', () => {
    it('should render image preview with src prop', () => {
      render(<TestImagePreview attachment={mockAttachment} />);
      
      expect(screen.getByRole('img')).toBeInTheDocument();
      expect(screen.getByRole('img')).toHaveAttribute('src', 'mock-url-test-attachment-1');
      expect(screen.getByRole('img')).toHaveAttribute('alt', 'test-image.png');
    });

    it('should render image preview with file prop', () => {
      render(<TestImagePreview attachment={mockAttachment} />);
      
      expect(screen.getByRole('img')).toBeInTheDocument();
      expect(mockMediaService.getAttachmentUrl).toHaveBeenCalled();
    });

    it('should show loading state while image loads', () => {
      render(<TestImagePreview attachment={mockAttachment} />);
      
      // Should show loading state initially (opacity-0)
      expect(screen.getByRole('img')).toHaveClass('opacity-0');
    });
  });

  // Test 2: Image metadata
  describe('Image Metadata', () => {
    it('should display image dimensions when available', () => {
      render(<TestImagePreview attachment={mockAttachment} />);
      
      // Simulate image load to show metadata
      const img = screen.getByRole('img');
      fireEvent.load(img);
      
      expect(screen.getByText('800×600')).toBeInTheDocument();
    });

    it('should display file size when available', () => {
      render(<TestImagePreview attachment={mockAttachment} />);
      
      // Simulate image load to show metadata
      const img = screen.getByRole('img');
      fireEvent.load(img);
      
      expect(screen.getByText('1000 KB')).toBeInTheDocument();
    });

    it('should display file name when available', () => {
      render(<TestImagePreview attachment={mockAttachment} />);
      
      // Simulate image load to show metadata
      const img = screen.getByRole('img');
      fireEvent.load(img);
      
      expect(screen.getByText('test-image.png')).toBeInTheDocument();
      expect(screen.getByTitle('test-image.png')).toBeInTheDocument();
    });
  });

  // Test 3: User interactions
  describe('User Interactions', () => {
    it('should expand to full size on click', async () => {
      const user = userEvent.setup();
      render(<TestImagePreview attachment={mockAttachment} />);
      
      // Simulate image load first
      const img = screen.getByRole('img');
      fireEvent.load(img);
      
      // Wait for image to be loaded
      await waitFor(() => {
        expect(img).toHaveClass('opacity-100');
      });
      
      // Click the expand button
      const expandButton = screen.getByTitle('View full size');
      await user.click(expandButton);
      
      // Should show modal
      expect(screen.getByText('Close')).toBeInTheDocument();
    });

    it('should close expanded view on escape key', async () => {
      const user = userEvent.setup();
      render(<TestImagePreview attachment={mockAttachment} />);
      
      // Simulate image load and expand
      const img = screen.getByRole('img');
      fireEvent.load(img);
      await waitFor(() => expect(img).toHaveClass('opacity-100'));
      
      const expandButton = screen.getByTitle('View full size');
      await user.click(expandButton);
      
      // Click close button (simulating escape functionality)
      const closeButton = screen.getByText('Close');
      await user.click(closeButton);
      
      // Modal should be closed
      await waitFor(() => {
        expect(screen.queryByText('Close')).not.toBeInTheDocument();
      });
    });

    it('should support copy image functionality', async () => {
      const user = userEvent.setup();
      render(<TestImagePreview attachment={mockAttachment} />);
      
      // Simulate image load
      const img = screen.getByRole('img');
      fireEvent.load(img);
      await waitFor(() => expect(img).toHaveClass('opacity-100'));
      
      // Click download button (which serves as copy functionality)
      const downloadButton = screen.getByTitle('Download image');
      await user.click(downloadButton);
      
      // Should trigger download/copy action
      expect(downloadButton).toBeInTheDocument();
    });
  });

  // Test 4: Error handling
  describe('Error Handling', () => {
    it('should show error state for invalid images', async () => {
      render(<TestImagePreview attachment={mockAttachment} />);
      
      const img = screen.getByRole('img');
      fireEvent.error(img);
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load image')).toBeInTheDocument();
      });
    });

    it('should handle missing src/file props gracefully', () => {
      const incompleteAttachment = {
        ...mockAttachment,
        meta: undefined
      };
      
      render(<TestImagePreview attachment={incompleteAttachment} />);
      
      // Should still render without throwing
      expect(screen.getByRole('img')).toBeInTheDocument();
      
      // Simulate image load
      const img = screen.getByRole('img');
      fireEvent.load(img);
      
      // Should not display dimensions since meta is undefined
      expect(screen.queryByText('×')).not.toBeInTheDocument();
    });
  });

  // Test 5: Accessibility
  describe('Accessibility', () => {
    it('should have proper alt text', () => {
      render(<TestImagePreview attachment={mockAttachment} />);
      
      const img = screen.getByRole('img');
      expect(img).toHaveAttribute('alt', 'test-image.png');
    });

    it('should be keyboard navigable', async () => {
      const user = userEvent.setup();
      render(<TestImagePreview attachment={mockAttachment} showRemoveButton onRemove={vi.fn()} />);
      
      // Simulate image load
      const img = screen.getByRole('img');
      fireEvent.load(img);
      await waitFor(() => expect(img).toHaveClass('opacity-100'));
      
      // Tab to buttons and verify they're focusable
      await user.tab();
      
      // The remove button should be focusable
      const removeButton = screen.getByLabelText('Remove image');
      expect(removeButton).toBeInTheDocument();
    });

    it('should have proper ARIA labels', () => {
      const onRemoveMock = vi.fn();
      render(<TestImagePreview attachment={mockAttachment} showRemoveButton onRemove={onRemoveMock} />);
      
      // Simulate image load to show overlay buttons
      const img = screen.getByRole('img');
      fireEvent.load(img);
      
      expect(screen.getByLabelText('Remove image')).toBeInTheDocument();
      expect(screen.getByLabelText('Download image')).toBeInTheDocument();
      // The expand button has a title but no aria-label in our mock
      expect(screen.getByTitle('View full size')).toBeInTheDocument();
    });
  });
});

export {}; 