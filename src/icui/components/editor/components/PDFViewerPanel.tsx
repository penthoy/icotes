/**
 * PDF Viewer Panel Component
 * 
 * Displays PDF files in the editor using Mozilla's PDF.js library (pdfjs-dist).
 * Renders PDF pages via canvas-based rendering for better control and features.
 * 
 * Features:
 * - Page-by-page rendering with PDF.js (pdfjs-dist dependency)
 * - Zoom controls and page navigation
 * - Download functionality
 * - Loading states and error handling
 * 
 * Future extension points:
 * - PDF annotations and highlighting
 * - Text extraction and search
 */

import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';

import {
  getDocument,
  GlobalWorkerOptions,
  type PDFDocumentProxy,
} from 'pdfjs-dist/legacy/build/pdf.mjs';

// Vite: load the worker as a URL
import workerSrc from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';

GlobalWorkerOptions.workerSrc = workerSrc;


interface PDFPageCanvasProps {
  pdfDocument: PDFDocumentProxy;
  pageNumber: number;
  scale: number;
}

const PDFPageCanvas: React.FC<PDFPageCanvasProps> = ({ pdfDocument, pageNumber, scale }) => {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null);

  const [isVisible, setIsVisible] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [renderError, setRenderError] = useState(false);

  useEffect(() => {
    if (!wrapperRef.current) return;

    if (typeof IntersectionObserver === 'undefined') {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setIsVisible(true);
        }
      },
      { root: null, rootMargin: '600px 0px' }
    );

    observer.observe(wrapperRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isVisible) return;
    if (!canvasRef.current) return;

    let cancelled = false;
    setIsRendering(true);
    setRenderError(false);

    (async () => {
      try {
        const page = await pdfDocument.getPage(pageNumber);
        if (cancelled || !canvasRef.current) return;

        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d', { alpha: false });
        if (!context) throw new Error('Could not get 2D context');

        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;

        context.setTransform(dpr, 0, 0, dpr, 0, 0);

        renderTaskRef.current?.cancel();
        const renderTask = page.render({ canvasContext: context, viewport });
        renderTaskRef.current = renderTask as unknown as { cancel: () => void };

        await renderTask.promise;
        if (cancelled) return;
        setIsRendering(false);
      } catch {
        if (cancelled) return;
        setRenderError(true);
        setIsRendering(false);
      }
    })();

    return () => {
      cancelled = true;
      renderTaskRef.current?.cancel();
    };
  }, [isVisible, pdfDocument, pageNumber, scale]);

  return (
    <div
      ref={wrapperRef}
      className="rounded-md overflow-hidden"
      style={{
        backgroundColor: '#ffffff',
        boxShadow: '0 1px 10px rgba(0,0,0,0.25)',
      }}
    >
      {renderError ? (
        <div
          className="p-4 text-sm"
          style={{ color: 'var(--icui-text-secondary)', backgroundColor: 'var(--icui-bg-secondary)' }}
        >
          Failed to render page {pageNumber}.
        </div>
      ) : (
        <div className="relative">
          <canvas ref={canvasRef} />
          {isRendering && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div
                className="text-xs px-2 py-1 rounded"
                style={{
                  backgroundColor: 'rgba(0,0,0,0.55)',
                  color: '#fff',
                }}
              >
                Rendering...
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface PDFViewerPanelProps {
  filePath: string;
  fileName: string;
}

export const PDFViewerPanel: React.FC<PDFViewerPanelProps> = ({ filePath, fileName }) => {
  const [pdfDocument, setPdfDocument] = useState<PDFDocumentProxy | null>(null);
  const [pdfLoaded, setPdfLoaded] = useState(false);
  const [pdfError, setPdfError] = useState(false);
  const [scale, setScale] = useState(1.25);

  const pdfUrl = `/api/files/raw?path=${encodeURIComponent(filePath)}`;

  const pageNumbers = useMemo(() => {
    if (!pdfDocument) return [];
    return Array.from({ length: pdfDocument.numPages }, (_, i) => i + 1);
  }, [pdfDocument]);

  useEffect(() => {
    let cancelled = false;

    setPdfLoaded(false);
    setPdfError(false);
    setPdfDocument(null);

    const loadingTask = getDocument(pdfUrl);

    loadingTask.promise
      .then((doc) => {
        if (cancelled) return;
        setPdfDocument(doc);
        setPdfLoaded(true);
      })
      .catch(() => {
        if (cancelled) return;
        setPdfError(true);
        setPdfLoaded(false);
      });

    return () => {
      cancelled = true;
      // Best-effort: release worker resources
      loadingTask.destroy();
    };
  }, [pdfUrl]);

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
      <div
        className="flex items-center justify-between px-3 py-2 border-b"
        style={{
          backgroundColor: 'var(--icui-bg-secondary)',
          borderColor: 'var(--icui-border-subtle)',
        }}
      >
        <div className="text-xs truncate" style={{ color: 'var(--icui-text-secondary)' }}>
          {fileName}
        </div>
        <div className="flex items-center gap-2">
          <button
            className="px-2 py-1 rounded text-xs"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            onClick={() => setScale((s) => Math.max(0.5, Math.round((s - 0.1) * 100) / 100))}
            type="button"
            aria-label="Zoom out"
          >
            −
          </button>
          <div className="text-xs" style={{ color: 'var(--icui-text-secondary)', minWidth: 54, textAlign: 'center' }}>
            {Math.round(scale * 100)}%
          </div>
          <button
            className="px-2 py-1 rounded text-xs"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            onClick={() => setScale((s) => Math.min(3, Math.round((s + 0.1) * 100) / 100))}
            type="button"
            aria-label="Zoom in"
          >
            +
          </button>
          <button
            onClick={handleDownload}
            className="px-3 py-1 rounded text-xs"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            type="button"
          >
            Download
          </button>
        </div>
      </div>

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

        {/* Custom PDF renderer (themeable scrollbars & background) */}
        {!pdfError && pdfLoaded && pdfDocument && (
          <div
            className="absolute inset-0 overflow-auto"
            style={{
              backgroundColor: 'var(--icui-bg-primary)',
            }}
          >
            <div className="py-6 px-4 flex flex-col items-center gap-6">
              {pageNumbers.map((pageNumber) => (
                <PDFPageCanvas
                  key={pageNumber}
                  pdfDocument={pdfDocument}
                  pageNumber={pageNumber}
                  scale={scale}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
