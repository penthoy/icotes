import React from 'react';

export interface NamespaceBadgeProps {
  namespace: string;
  isRemote?: boolean;
  className?: string;
}

/**
 * Small badge showing current namespace context, e.g. [💻 local] or [📡 hop1]
 */
export const NamespaceBadge: React.FC<NamespaceBadgeProps> = ({ namespace, isRemote = false, className = '' }) => {
  const icon = isRemote ? '📡' : '💻';
  const bg = isRemote ? 'rgba(59,130,246,0.15)' : 'rgba(148,163,184,0.15)';
  const border = isRemote ? 'rgba(59,130,246,0.45)' : 'rgba(148,163,184,0.45)';
  const color = isRemote ? 'var(--icui-accent, #60a5fa)' : 'var(--icui-text-secondary, #94a3b8)';
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs px-2 py-[2px] rounded-full ${className}`}
      style={{ backgroundColor: bg, border: `1px solid ${border}`, color }}
      title={isRemote ? 'Remote context' : 'Local context'}
    >
      <span aria-hidden>{icon}</span>
      <span className="font-medium">{namespace}</span>
    </span>
  );
};

export default NamespaceBadge;
