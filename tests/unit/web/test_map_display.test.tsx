import { describe, it, expect, vi } from 'vitest';

/**
 * MapDisplay Component Tests
 *
 * NOTE: Map components use Leaflet which requires browser-specific APIs (canvas, DOM).
 * Full visual and interaction testing is done via Storybook stories.
 * These unit tests verify exports and type contracts.
 */

// Mock leaflet-draw before it gets imported (it checks for global L)
vi.mock('leaflet-draw', () => ({}));
vi.mock('react-leaflet-draw', () => ({
  EditControl: () => null,
}));

// Mock react-leaflet
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="popup">{children}</div>
  ),
  FeatureGroup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="feature-group">{children}</div>
  ),
  useMap: () => ({
    fitBounds: vi.fn(),
    setView: vi.fn(),
  }),
  useMapEvents: () => null,
}));

// Mock leaflet module
vi.mock('leaflet', () => ({
  default: {
    Icon: {
      Default: {
        prototype: {},
        mergeOptions: vi.fn(),
      },
    },
    latLngBounds: vi.fn(() => ({
      extend: vi.fn(),
    })),
    polygon: vi.fn(() => ({})),
  },
}));

// Mock @turf/turf (used by BoundaryDrawer but may be imported transitively)
vi.mock('@turf/turf', () => ({
  polygon: vi.fn(() => ({})),
  area: vi.fn(() => 1000000),
  length: vi.fn(() => 4),
  centroid: vi.fn(() => ({
    geometry: { coordinates: [36.8219, -1.2921] },
  })),
}));

import { render, screen } from '@testing-library/react';
import { MapDisplay, ThemeProvider } from '@fp/ui-components';
import type { MapMarker, MapDisplayProps } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('MapDisplay', () => {
  describe('exports', () => {
    it('exports MapDisplay component', () => {
      expect(MapDisplay).toBeDefined();
      expect(typeof MapDisplay).toBe('function');
    });

    it('exports MapMarker type (verified via TypeScript)', () => {
      const marker: MapMarker = {
        id: '1',
        lat: -1.2921,
        lng: 36.8219,
        title: 'Test Location',
      };
      expect(marker.id).toBe('1');
    });

    it('exports MapDisplayProps type (verified via TypeScript)', () => {
      const props: MapDisplayProps = {
        markers: [],
        centerLat: -1.2921,
        centerLng: 36.8219,
        zoom: 10,
      };
      expect(props.zoom).toBe(10);
    });
  });

  describe('rendering', () => {
    it('renders without crashing', () => {
      renderWithTheme(<MapDisplay />);
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    it('renders with markers', () => {
      const markers: MapMarker[] = [
        { id: '1', lat: -1.2921, lng: 36.8219, title: 'Nairobi' },
        { id: '2', lat: -0.4167, lng: 36.95, title: 'Nyeri' },
      ];

      renderWithTheme(<MapDisplay markers={markers} />);

      const markerElements = screen.getAllByTestId('marker');
      expect(markerElements).toHaveLength(2);
    });

    it('renders tile layer', () => {
      renderWithTheme(<MapDisplay />);
      expect(screen.getByTestId('tile-layer')).toBeInTheDocument();
    });
  });

  describe('props', () => {
    it('accepts custom height', () => {
      const { container } = renderWithTheme(<MapDisplay height={500} />);
      expect(container.firstChild).toBeInTheDocument();
    });

    it('accepts custom center coordinates', () => {
      renderWithTheme(<MapDisplay centerLat={-0.5} centerLng={37.0} />);
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    it('accepts fitBounds prop', () => {
      const markers: MapMarker[] = [
        { id: '1', lat: -1.2921, lng: 36.8219 },
      ];

      renderWithTheme(<MapDisplay markers={markers} fitBounds />);
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });
});
