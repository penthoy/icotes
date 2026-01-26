/**
 * Language Selector Modal Component
 * 
 * Modal dialog for selecting programming language when file extension is not recognized
 */

import React from 'react';
import { supportedFileTypes as supportedLanguages } from '../utils/fileTypeDetection';

interface LanguageSelectorModalProps {
  fileName: string;
  onSelect: (languageId: string) => void;
  onCancel: () => void;
}

export const LanguageSelectorModal: React.FC<LanguageSelectorModalProps> = ({
  fileName,
  onSelect,
  onCancel
}) => {

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onCancel}
    >
      <div 
        className="icui-modal rounded-lg shadow-lg p-6 max-w-md w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold mb-4">Select Language Highlighting</h3>
        <p className="text-sm mb-4 icui-text-secondary">
          The file extension for "{fileName}" is not recognized. Please select a syntax highlighting mode:
        </p>
        <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto">
          {supportedLanguages.map((lang) => (
            <button
              key={lang.id}
              onClick={() => onSelect(lang.id)}
              className="icui-language-button text-sm"
            >
              {lang.name}
            </button>
          ))}
        </div>
        <div className="flex justify-end mt-4 space-x-2">
          <button
            onClick={onCancel}
            className="icui-button-secondary text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
