/**
 * ICUI Mobile Tab Bar
 * Fixed bottom navigation bar for mobile layout mode with touch-friendly tabs
 */

import React from 'react';

export interface MobileTab {
  id: string;
  icon: string;
  label: string;
  badge?: number;
}

export interface ICUIMobileTabBarProps {
  tabs: MobileTab[];
  activeTabId: string;
  onTabChange: (tabId: string) => void;
  onOpenMobileSettings?: () => void;
  className?: string;
}

export const ICUIMobileTabBar: React.FC<ICUIMobileTabBarProps> = ({
  tabs,
  activeTabId,
  onTabChange,
  onOpenMobileSettings,
  className = '',
}) => {
  return (
    <div
      className={`icui-mobile-tab-bar fixed bottom-0 left-0 right-0 z-50 ${className}`}
      style={{
        backgroundColor: 'var(--icui-bg-secondary)',
        borderTop: '1px solid var(--icui-border)',
        height: '60px',
        display: 'flex',
        alignItems: 'stretch',
        justifyContent: 'space-between',
        padding: '0',
      }}
    >
      <div className="flex-1 flex items-stretch" style={{ minWidth: 0 }}>
        {tabs.map((tab) => {
          const isActive = tab.id === activeTabId;

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className="icui-mobile-tab flex-1 flex flex-col items-center justify-center relative"
              style={{
                minWidth: '44px',
                minHeight: '44px',
                border: 'none',
                background: 'transparent',
                color: isActive ? 'var(--icui-text-primary)' : 'var(--icui-text-muted)',
                fontSize: '24px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                WebkitTapHighlightColor: 'transparent',
              }}
              aria-label={tab.label}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="tab-icon" style={{ fontSize: '24px', marginBottom: '2px' }}>
                {tab.icon}
              </span>
              <span
                className="tab-label"
                style={{
                  fontSize: '10px',
                  fontWeight: isActive ? 600 : 400,
                  lineHeight: 1,
                }}
              >
                {tab.label}
              </span>

              {/* Active indicator */}
              {isActive && (
                <div
                  className="tab-indicator absolute"
                  style={{
                    top: 0,
                    left: '20%',
                    right: '20%',
                    height: '3px',
                    backgroundColor: 'var(--icui-accent)',
                    borderRadius: '0 0 3px 3px',
                  }}
                />
              )}

              {/* Badge for notifications */}
              {tab.badge !== undefined && tab.badge > 0 && (
                <div
                  className="tab-badge absolute"
                  style={{
                    top: '4px',
                    right: '25%',
                    backgroundColor: 'var(--icui-error, #ef4444)',
                    color: 'white',
                    borderRadius: '10px',
                    padding: '2px 6px',
                    fontSize: '10px',
                    fontWeight: 600,
                    minWidth: '18px',
                    textAlign: 'center',
                    lineHeight: '14px',
                  }}
                >
                  {tab.badge > 99 ? '99+' : tab.badge}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Kebab menu shortcut (mobile settings) */}
      <button
        type="button"
        onClick={onOpenMobileSettings}
        disabled={!onOpenMobileSettings}
        className="icui-mobile-tab-kebab flex items-center justify-center"
        style={{
          width: '56px',
          minWidth: '56px',
          minHeight: '44px',
          border: 'none',
          background: 'transparent',
          color: 'var(--icui-text-muted)',
          fontSize: '22px',
          cursor: onOpenMobileSettings ? 'pointer' : 'default',
          WebkitTapHighlightColor: 'transparent',
        }}
        aria-label="Mobile Settings"
        title="Mobile Settings"
      >
        <span aria-hidden="true" style={{ lineHeight: 1 }}>
          ⋮
        </span>
      </button>
    </div>
  );
};
