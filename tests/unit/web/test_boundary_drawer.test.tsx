import { describe, it, expect, vi } from 'vitest';

/**
 * BoundaryDrawer Component Tests
 *
 * NOTE: Map components use Leaflet and leaflet-draw which require browser-specific APIs.
 * Full visual and interaction testing is done via Storybook stories.
 * These unit tests verify exports, type contracts, and non-Leaflet logic.
 */

// Mock leaflet-draw before it gets imported (it checks for global L)
vi.mock('leaflet-draw', () => ({}));
vi.mock('react-leaflet-draw', () => ({
  EditControl: () => <div data-testid="edit-control" />,
}));

// Mock react-leaflet
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  FeatureGroup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="feature-group">{children}</div>
  ),
  Marker: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="popup">{children}</div>
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
    polygon: vi.fn(() => ({
      addTo: vi.fn(),
    })),
  },
}));

// Mock @turf/turf
vi.mock('@turf/turf', () => ({
  polygon: vi.fn(() => ({})),
  area: vi.fn(() => 1000000), // 1 km²
  length: vi.fn(() => 4), // 4 km perimeter
  centroid: vi.fn(() => ({
    geometry: {
      coordinates: [36.8219, -1.2921], // [lng, lat]
    },
  })),
}));

import { render, screen } from '@testing-library/react';
import { BoundaryDrawer, ThemeProvider } from '@fp/ui-components';
import type {
  BoundaryDrawerProps,
  GeoJSONPolygon,
  BoundaryMapMarker,
  BoundaryStats,
} from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('BoundaryDrawer', () => {
  describe('exports', () => {
    it('exports BoundaryDrawer component', () => {
      expect(BoundaryDrawer).toBeDefined();
      expect(typeof BoundaryDrawer).toBe('function');
    });

    it('exports GeoJSONPolygon type (verified via TypeScript)', () => {
      const polygon: GeoJSONPolygon = {
        type: 'Polygon',
        coordinates: [
          [
            [36.8, -1.3],
            [36.9, -1.3],
            [36.9, -1.2],
            [36.8, -1.2],
            [36.8, -1.3],
          ],
        ],
      };
      expect(polygon.type).toBe('Polygon');
      expect(polygon.coordinates.length).toBe(1);
    });

    it('exports BoundaryMapMarker type (verified via TypeScript)', () => {
      const marker: BoundaryMapMarker = {
        id: '1',
        lat: -1.2921,
        lng: 36.8219,
        title: 'Collection Point 1',
      };
      expect(marker.id).toBe('1');
    });

    it('exports BoundaryStats type (verified via TypeScript)', () => {
      const stats: BoundaryStats = {
        areaKm2: 1.5,
        perimeterKm: 5.2,
        centroid: { lat: -1.2921, lng: 36.8219 },
      };
      expect(stats.areaKm2).toBe(1.5);
    });

    it('exports BoundaryDrawerProps type (verified via TypeScript)', () => {
      const props: BoundaryDrawerProps = {
        onBoundaryChange: vi.fn(),
      };
      expect(typeof props.onBoundaryChange).toBe('function');
    });
  });

  describe('rendering', () => {
    it('renders without crashing', () => {
      const handleChange = vi.fn();

      renderWithTheme(<BoundaryDrawer onBoundaryChange={handleChange} />);

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    it('renders tile layer', () => {
      const handleChange = vi.fn();

      renderWithTheme(<BoundaryDrawer onBoundaryChange={handleChange} />);

      expect(screen.getByTestId('tile-layer')).toBeInTheDocument();
    });

    it('renders edit control when not disabled', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <BoundaryDrawer onBoundaryChange={handleChange} disabled={false} />
      );

      expect(screen.getByTestId('edit-control')).toBeInTheDocument();
    });

    it('hides edit control when disabled', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <BoundaryDrawer onBoundaryChange={handleChange} disabled={true} />
      );

      expect(screen.queryByTestId('edit-control')).not.toBeInTheDocument();
    });

    it('renders existing markers', () => {
      const handleChange = vi.fn();
      const markers: BoundaryMapMarker[] = [
        { id: '1', lat: -1.2921, lng: 36.8219, title: 'CP1' },
        { id: '2', lat: -1.3, lng: 36.85, title: 'CP2' },
      ];

      renderWithTheme(
        <BoundaryDrawer
          onBoundaryChange={handleChange}
          existingMarkers={markers}
        />
      );

      const markerElements = screen.getAllByTestId('marker');
      expect(markerElements).toHaveLength(2);
    });

    it('displays stats when boundary exists', () => {
      const handleChange = vi.fn();
      const boundary: GeoJSONPolygon = {
        type: 'Polygon',
        coordinates: [
          [
            [36.8, -1.3],
            [36.9, -1.3],
            [36.9, -1.2],
            [36.8, -1.2],
            [36.8, -1.3],
          ],
        ],
      };

      renderWithTheme(
        <BoundaryDrawer
          onBoundaryChange={handleChange}
          existingBoundary={boundary}
        />
      );

      // Stats should be displayed
      expect(screen.getByLabelText('Boundary area')).toBeInTheDocument();
      expect(screen.getByLabelText('Boundary perimeter')).toBeInTheDocument();
      expect(screen.getByLabelText('Boundary centroid')).toBeInTheDocument();
    });

    it('shows help text when not disabled', () => {
      const handleChange = vi.fn();

      renderWithTheme(<BoundaryDrawer onBoundaryChange={handleChange} />);

      expect(
        screen.getByText(/use the polygon tool/i)
      ).toBeInTheDocument();
    });

    it('shows disabled message when disabled', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <BoundaryDrawer onBoundaryChange={handleChange} disabled />
      );

      expect(screen.getByText(/editing is disabled/i)).toBeInTheDocument();
    });
  });

  describe('props', () => {
    it('accepts custom height', () => {
      const handleChange = vi.fn();

      const { container } = renderWithTheme(
        <BoundaryDrawer onBoundaryChange={handleChange} height={600} />
      );

      expect(container.firstChild).toBeInTheDocument();
    });

    it('accepts custom default center', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <BoundaryDrawer
          onBoundaryChange={handleChange}
          defaultCenter={{ lat: -0.4167, lng: 36.95 }}
        />
      );

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    it('accepts custom default zoom', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <BoundaryDrawer onBoundaryChange={handleChange} defaultZoom={12} />
      );

      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });
});
