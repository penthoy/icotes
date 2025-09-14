/**
 * Phase 3 UI Components Test (fixed)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import UploadWidget from '../../../src/icui/components/media/upload/UploadWidget';
import UploadItem from '../../../src/icui/components/media/upload/UploadItem';
import AttachmentPreview from '../../../src/icui/components/media/AttachmentPreview';
import ImagePreview from '../../../src/icui/components/media/ImagePreview';
import type { UploadItem as UploadItemType } from '../../../src/icui/hooks/useMediaUpload';
import type { MediaAttachment } from '../../../src/icui/services/mediaService';

vi.mock('../../../src/icui/hooks/useMediaUpload', () => ({
  useMediaUpload: () => ({
    queue: [],
    uploads: [],
    isUploading: false,
    addFiles: vi.fn(),
    removeFile: vi.fn(),
    clearCompleted: vi.fn(),
    uploadAll: vi.fn().mockResolvedValue([]),
  }),
}));

vi.mock('../../../src/icui/services/mediaService', () => ({
  mediaService: {
    getAttachmentUrl: (attachment: MediaAttachment) => `/api/media/file/${attachment.id}`,
    validateFile: () => ({ valid: true }),
  },
  default: {
    getAttachmentUrl: (attachment: MediaAttachment) => `/api/media/file/${attachment.id}`,
    validateFile: () => ({ valid: true }),
  }
}));

describe('Phase 3 Media Components', () => {
  describe('UploadWidget', () => {
    const defaultProps = {
      isOpen: true,
      onClose: vi.fn(),
      onFilesUploaded: vi.fn(),
    };

    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('renders when open', () => {
      render(<UploadWidget {...defaultProps} />);
      expect(screen.getByText('Upload Files')).toBeInTheDocument();
      expect(screen.getByText(/Drop files here or/)).toBeInTheDocument();
      expect(screen.getByText(/browse/)).toBeInTheDocument();
    });

    it('hides when closed', () => {
      render(<UploadWidget {...defaultProps} isOpen={false} />);
      expect(screen.queryByText('Upload Files')).not.toBeInTheDocument();
    });

    it('shows file count limit', () => {
      render(<UploadWidget {...defaultProps} maxFiles={5} />);
      expect(screen.getByText('(0/5)')).toBeInTheDocument();
    });
  });

  describe('UploadItem', () => {
    const mockFile = new File(['test content'], 'test.jpg', { type: 'image/jpeg' });
    const createUploadItem = (status: UploadItemType['status'], progress = 0): UploadItemType => ({
      id: 'test-1',
      file: mockFile,
      status,
      progress,
      error: status === 'error' ? 'Upload failed' : undefined,
    });

    it('renders file info', () => {
      const item = createUploadItem('pending');
      render(<UploadItem item={item} onRemove={vi.fn()} />);
      expect(screen.getByText('test.jpg')).toBeInTheDocument();
      expect(screen.getByText(/12 Bytes/)).toBeInTheDocument();
      expect(screen.getByText('pending')).toBeInTheDocument();
    });
  });

  describe('AttachmentPreview', () => {
    const mockAttachment: MediaAttachment = {
      id: 'att-1',
      kind: 'image',
      path: 'uploads/att-1_image.jpg',
      mime: 'image/jpeg',
      size: 1024,
      meta: { original_name: 'vacation.jpg' }
    };
    it('renders attachment info', () => {
      render(<AttachmentPreview attachment={mockAttachment} />);
      expect(screen.getByText('vacation.jpg')).toBeInTheDocument();
      expect(screen.getByText('1 KB')).toBeInTheDocument();
      // Kind label is lowercase in component
      expect(screen.getByText('image')).toBeInTheDocument();
    });
  });

  describe('ImagePreview', () => {
    const mockImageAttachment: MediaAttachment = {
      id: 'img-1',
      kind: 'image',
      path: 'uploads/img-1_photo.jpg',
      mime: 'image/jpeg',
      size: 2048,
      meta: { original_name: 'photo.jpg', dimensions: { width: 800, height: 600 } }
    };
    it('renders image info', () => {
      render(<ImagePreview attachment={mockImageAttachment} />);
      expect(screen.getByText('photo.jpg')).toBeInTheDocument();
      expect(screen.getByText('2 KB')).toBeInTheDocument();
    });
    it('handles image load error', async () => {
      render(<ImagePreview attachment={mockImageAttachment} />);
      const img = screen.getByRole('img');
      fireEvent.error(img);
      await waitFor(() => expect(screen.getByText('Failed to load image')).toBeInTheDocument());
    });
  });
});

console.log('✅ Phase 3 UI Components tests executed');