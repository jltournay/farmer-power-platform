/**
 * Factory Portal Entry Point
 *
 * Initializes the React application with all required providers.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { AuthProvider } from '@fp/auth';
import { App } from './app/App';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element not found');
}

// Get base URL from Vite env (e.g., "/factory/") and convert to basename (e.g., "/factory")
const basename = (import.meta.env.VITE_BASE_URL || '/').replace(/\/$/, '') || '/';

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
);
