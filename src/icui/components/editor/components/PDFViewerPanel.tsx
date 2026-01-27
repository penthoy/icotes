/**
 * PDF Viewer Panel Component
 * 
 * Displays PDF files in the editor using the browser's native PDF viewer.
 * Follows the same pattern as ImageViewerPanel for consistency.
 * 
 * Features:
 * - Native browser PDF rendering (no external dependencies)
 * - Loading states and error handling
 * - Full-screen PDF viewing with browser's built-in controls
 * - Download functionality
 * 
 * Future extension points:
 * - Custom PDF controls (zoom, page navigation)
 * - PDF annotations and highlighting
 * - Text extraction and search
 */

import React, { useState, useCallback } from 'react';

interface PDFViewerPanelProps {
  filePath: string;
  fileName: string;
}

export const PDFViewerPanel: React.FC<PDFViewerPanelProps> = ({ filePath, fileName }) => {
  // PDF loading state
  const [pdfLoaded, setPdfLoaded] = useState(false);
  const [pdfError, setPdfError] = useState(false);

  const pdfUrl = `/api/files/raw?path=${encodeURIComponent(filePath)}`;

  /**
   * Handle PDF load success
   */
  const handlePdfLoad = useCallback(() => {
    setPdfLoaded(true);
    setPdfError(false);
  }, []);

  /**
   * Handle PDF load error
   */
  const handlePdfError = useCallback(() => {
    setPdfError(true);
    setPdfLoaded(false);
  }, []);

  /**
   * Download the PDF file
   */
  const handleDownload = useCallback(() => {
    const link = document.createElement('a');
    link.href = pdfUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [pdfUrl, fileName]);

  return (
    <div 
      className="flex flex-col h-full w-full"
      style={{ 
        backgroundColor: 'var(--icui-bg-primary)',
        color: 'var(--icui-text-primary)'
      }}
    >
      {/* PDF Viewer Container */}
      <div className="flex-1 relative overflow-hidden">
        {/* Loading state */}
        {!pdfLoaded && !pdfError && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin text-4xl mb-2">⏳</div>
              <p className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
                Loading PDF...
              </p>
            </div>
          </div>
        )}

        {/* Error state */}
        {pdfError && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div 
              className="text-center p-6 rounded-lg max-w-md"
              style={{ 
                backgroundColor: 'var(--icui-bg-secondary)',
                border: '1px solid var(--icui-border-subtle)'
              }}
            >
              <div className="text-4xl mb-3">⚠️</div>
              <h3 className="text-lg font-semibold mb-2">Failed to Load PDF</h3>
              <p className="text-sm mb-4" style={{ color: 'var(--icui-text-secondary)' }}>
                The PDF file could not be loaded. It may be corrupted or your browser may not support this PDF format.
              </p>
              <button
                onClick={handleDownload}
                className="px-4 py-2 rounded transition-colors"
                style={{
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  color: 'var(--icui-text-primary)'
                }}
              >
                Download PDF
              </button>
            </div>
          </div>
        )}

        {/* PDF iframe - uses browser's native PDF viewer */}
        {/* Note: We don't use sandbox attribute as it blocks PDF rendering in most browsers */}
        <iframe
          src={pdfUrl}
          title={fileName}
          className="w-full h-full border-0"
          style={{ 
            display: pdfError ? 'none' : 'block',
            backgroundColor: '#525659' // Standard PDF viewer background
          }}
          onLoad={handlePdfLoad}
          onError={handlePdfError}
        />
      </div>
    </div>
  );
};
