/**
 * Platform Admin Entry Point
 *
 * Initializes the React application with all required providers.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { AuthProvider } from '@fp/auth';
import { App } from './app/App';

// Leaflet CSS imports for map components (per ADR-017)
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element not found');
}

// Get base URL from Vite env (e.g., "/admin/") and convert to basename (e.g., "/admin")
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
