/**
 * Factory Portal Root Component
 *
 * Sets up routing and layout for the Factory Portal application.
 */

import { useRoutes } from 'react-router-dom';
import { useAuth, MockLoginSelector } from '@fp/auth';
import { routes } from './routes';

/**
 * Root application component.
 *
 * Handles authentication flow and route rendering.
 */
export function App(): JSX.Element {
  const { showLoginSelector, selectMockUser } = useAuth();
  const routeElements = useRoutes(routes);

  // Show mock login selector when in development mode
  if (showLoginSelector) {
    return <MockLoginSelector onSelect={selectMockUser} />;
  }

  return <>{routeElements}</>;
}
