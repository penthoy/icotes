/**
 * Navigation Helper Component
 * 
 * Simple navigation component to help access different test routes
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const routes = [
  { path: '/', label: 'Home', description: 'Main application' },
  { path: '/integration', label: 'Integration Test', description: 'ICUI-ICPY Backend Integration Test' },
  { path: '/simple-terminal', label: 'Simple Terminal', description: 'Simple terminal implementation' },
  { path: '/icui-test', label: 'ICUI Test', description: 'Basic ICUI components test' },
  { path: '/icui-test2', label: 'ICUI Test 2', description: 'Advanced ICUI components test' },
  { path: '/icui-test3', label: 'ICUI Test 3', description: 'ICUI layout test' },
  { path: '/icui-test4', label: 'ICUI Test 4', description: 'ICUI editor test' },
  { path: '/icui-test4.5', label: 'ICUI Test 4.5', description: 'ICUI enhanced test' },
  { path: '/icui-test4.9', label: 'ICUI Test 4.9', description: 'ICUI latest test' },
  { path: '/icui-test6', label: 'ICUI Test 6', description: 'ICUI test 6' },
  { path: '/icui-test7', label: 'ICUI Test 7', description: 'ICUI test 7' },
  { path: '/icui-test8.2', label: 'ICUI Test 8.2', description: 'Explorer extensibility test' },
  { path: '/icui-test8.3', label: 'ICUI Test 8.3', description: 'Chat History session context menus' },
  { path: '/icui-editor-comparison', label: 'Editor Comparison', description: 'Editor comparison test' },
  { path: '/icui-layouts', label: 'Reference Layouts', description: 'Layout reference test' },
  { path: '/icui-main', label: 'ICUI Main', description: 'Main ICUI page' },
  { path: '/icui-enhanced', label: 'ICUI Enhanced', description: 'Enhanced ICUI components' },
  { path: '/icui-terminal-test', label: 'Terminal Test', description: 'Terminal component test' }
];

export const NavigationHelper: React.FC = () => {
  const location = useLocation();
  
  return (
    <div className="navigation-helper" style={{ 
      position: 'fixed', 
      top: 0, 
      right: 0, 
      width: '300px', 
      height: '100vh', 
      backgroundColor: '#f5f5f5', 
      borderLeft: '1px solid #ddd',
      overflowY: 'auto',
      zIndex: 1000,
      padding: '20px',
      fontSize: '14px'
    }}>
      <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Navigation</h3>
      <div style={{ marginBottom: '20px' }}>
        <strong>Current:</strong> {location.pathname}
      </div>
      
      <div style={{ marginBottom: '20px' }}>
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#e8f4f8', 
          borderRadius: '4px',
          border: '1px solid #2196F3'
        }}>
          <strong>🚀 Integration Test</strong>
          <br />
          <Link 
            to="/integration" 
            style={{ 
              color: '#2196F3', 
              textDecoration: 'none',
              fontWeight: 'bold'
            }}
          >
            /integration
          </Link>
          <br />
          <small>Backend integration testing environment</small>
        </div>
      </div>
      
      <div>
        <h4>All Routes:</h4>
        {routes.map((route) => (
          <div key={route.path} style={{ 
            marginBottom: '10px',
            padding: '8px',
            backgroundColor: location.pathname === route.path ? '#e3f2fd' : '#fff',
            borderRadius: '4px',
            border: '1px solid #eee'
          }}>
            <Link 
              to={route.path} 
              style={{ 
                color: location.pathname === route.path ? '#1976d2' : '#333',
                textDecoration: 'none',
                fontWeight: location.pathname === route.path ? 'bold' : 'normal'
              }}
            >
              {route.label}
            </Link>
            <br />
            <small style={{ color: '#666' }}>{route.description}</small>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NavigationHelper;
