/**
 * ImageViewerPanel Component Tests
 * 
 * Tests for the image viewer with zoom and pan functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ImageViewerPanel } from '../../icui/components/editor/components/ImageViewerPanel';

// Mock image loading behavior
const mockNaturalWidth = 1024;
const mockNaturalHeight = 768;

describe('ImageViewerPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders with filename in info bar', () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      expect(screen.getByText('test.png')).toBeInTheDocument();
    });

    it('shows loading spinner before image loads', () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Check for spinning animation element
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });

    it('shows error state when image fails to load', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/broken.png" 
          fileName="broken.png" 
        />
      );
      
      // Simulate image error
      const img = document.querySelector('img');
      if (img) {
        fireEvent.error(img);
      }
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to load image/)).toBeInTheDocument();
      });
    });

    it('shows dimensions after image loads', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load with dimensions
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: mockNaturalWidth });
        Object.defineProperty(img, 'naturalHeight', { value: mockNaturalHeight });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        expect(screen.getByText(`${mockNaturalWidth} × ${mockNaturalHeight}`)).toBeInTheDocument();
      });
    });
  });

  describe('Toolbar', () => {
    it('shows toolbar after image loads', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: mockNaturalWidth });
        Object.defineProperty(img, 'naturalHeight', { value: mockNaturalHeight });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        // Check for toolbar buttons
        expect(screen.getByTitle(/Zoom Tool/)).toBeInTheDocument();
        expect(screen.getByTitle(/Pan Tool/)).toBeInTheDocument();
        expect(screen.getByText('Fit')).toBeInTheDocument();
        expect(screen.getByText('100%')).toBeInTheDocument();
      });
    });

    it('pan tool is active by default', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: mockNaturalWidth });
        Object.defineProperty(img, 'naturalHeight', { value: mockNaturalHeight });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        const panButton = screen.getByTitle(/Pan Tool/);
        // Check that pan tool has accent background (active state)
        expect(panButton).toHaveStyle({ backgroundColor: 'var(--icui-accent)' });
      });
    });

    it('switches to zoom tool when clicked', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: mockNaturalWidth });
        Object.defineProperty(img, 'naturalHeight', { value: mockNaturalHeight });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        const zoomButton = screen.getByTitle(/Zoom Tool/);
        fireEvent.click(zoomButton);
        expect(zoomButton).toHaveStyle({ backgroundColor: 'var(--icui-accent)' });
      });
    });
  });

  describe('Zoom Controls', () => {
    it('displays zoom percentage', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: mockNaturalWidth });
        Object.defineProperty(img, 'naturalHeight', { value: mockNaturalHeight });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        // Should show some percentage (could be fit-to-view calculated or 100%)
        const zoomDisplay = screen.getByTitle('Current zoom level');
        expect(zoomDisplay).toBeInTheDocument();
        expect(zoomDisplay.textContent).toMatch(/\d+%/);
      });
    });

    it('zooms in when zoom in button is clicked', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: 100 });
        Object.defineProperty(img, 'naturalHeight', { value: 100 });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        const zoomInButton = screen.getByTitle('Zoom In');
        const zoomDisplay = screen.getByTitle('Current zoom level');
        
        const initialZoom = parseInt(zoomDisplay.textContent || '0');
        fireEvent.click(zoomInButton);
        
        // Zoom should have increased by 25%
        const newZoom = parseInt(zoomDisplay.textContent || '0');
        expect(newZoom).toBeGreaterThan(initialZoom);
      });
    });

    it('zooms out when zoom out button is clicked', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: 100 });
        Object.defineProperty(img, 'naturalHeight', { value: 100 });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        const zoomInButton = screen.getByTitle('Zoom In');
        const zoomOutButton = screen.getByTitle('Zoom Out');
        const zoomDisplay = screen.getByTitle('Current zoom level');
        
        // First zoom in to have room to zoom out
        fireEvent.click(zoomInButton);
        fireEvent.click(zoomInButton);
        
        const zoomAfterIn = parseInt(zoomDisplay.textContent || '0');
        
        // Now zoom out
        fireEvent.click(zoomOutButton);
        
        // Zoom should have decreased by 25%
        const newZoom = parseInt(zoomDisplay.textContent || '0');
        expect(newZoom).toBeLessThan(zoomAfterIn);
      });
    });

    it('sets zoom to 100% when actual size button is clicked', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load with small dimensions (will fit below 100%)
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: 100 });
        Object.defineProperty(img, 'naturalHeight', { value: 100 });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        const actualSizeButton = screen.getByText('100%');
        const zoomDisplay = screen.getByTitle('Current zoom level');
        
        fireEvent.click(actualSizeButton);
        expect(zoomDisplay.textContent).toBe('100%');
      });
    });
  });

  describe('Mouse Wheel Zoom', () => {
    it('zooms with mouse wheel', async () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/test.png" 
          fileName="test.png" 
        />
      );
      
      // Simulate image load
      const img = document.querySelector('img');
      if (img) {
        Object.defineProperty(img, 'naturalWidth', { value: 100 });
        Object.defineProperty(img, 'naturalHeight', { value: 100 });
        fireEvent.load(img);
      }
      
      await waitFor(() => {
        const container = img?.closest('.flex-1');
        const zoomDisplay = screen.getByTitle('Current zoom level');
        
        if (container) {
          const initialZoom = parseInt(zoomDisplay.textContent || '0');
          
          // Scroll up should zoom in
          fireEvent.wheel(container, { deltaY: -100 });
          
          const newZoom = parseInt(zoomDisplay.textContent || '0');
          expect(newZoom).toBeGreaterThanOrEqual(initialZoom);
        }
      });
    });
  });

  describe('API URL Generation', () => {
    it('generates correct API URL for file path', () => {
      render(
        <ImageViewerPanel 
          filePath="/workspace/images/photo.jpg" 
          fileName="photo.jpg" 
        />
      );
      
      const img = document.querySelector('img');
      expect(img?.src).toContain('/api/files/raw?path=');
      expect(img?.src).toContain(encodeURIComponent('/workspace/images/photo.jpg'));
    });
  });
});
