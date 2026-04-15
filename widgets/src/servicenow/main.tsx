import React from 'react';
import { createRoot } from 'react-dom/client';
import { ErrorBoundary } from '../shared/ErrorBoundary';
import { McpBridgeProvider } from '../shared/McpBridge';
import { FluentWrapper } from '../shared/FluentWrapper';
import { ToastContainer } from '../shared/Toast';
import { ServiceNowApp } from './App';

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <McpBridgeProvider appName="gtc-snow-widget">
      <FluentWrapper>
        <ServiceNowApp />
        <ToastContainer />
      </FluentWrapper>
    </McpBridgeProvider>
  </ErrorBoundary>
);
