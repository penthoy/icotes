import React from 'react';

interface Props {
  onClick: () => void;
}

const JumpToLatestButton: React.FC<Props> = ({ onClick }) => {
  return (
    <div className="sticky bottom-2 flex justify-center z-10">
      <button
        onClick={onClick}
        className="px-3 py-1.5 text-xs rounded-full shadow border"
        style={{
          backgroundColor: 'var(--icui-bg-secondary)',
          color: 'var(--icui-text-primary)',
          borderColor: 'var(--icui-border-subtle)'
        }}
      >
        Jump to latest
      </button>
    </div>
  );
};

export default JumpToLatestButton;
