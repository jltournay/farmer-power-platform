import { describe, it, expect, vi } from 'vitest';

/**
 * GPSFieldWithMapAssist Component Tests
 *
 * NOTE: Map components use Leaflet which requires browser-specific APIs (canvas, DOM).
 * Full visual and interaction testing is done via Storybook stories.
 * These unit tests verify exports, type contracts, and text field behavior.
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
  Marker: () => <div data-testid="marker" />,
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

// Mock @turf/turf
vi.mock('@turf/turf', () => ({
  polygon: vi.fn(() => ({})),
  area: vi.fn(() => 1000000),
  length: vi.fn(() => 4),
  centroid: vi.fn(() => ({
    geometry: { coordinates: [36.8219, -1.2921] },
  })),
}));

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GPSFieldWithMapAssist, ThemeProvider } from '@fp/ui-components';
import type { GPSCoordinates, GPSFieldWithMapAssistProps } from '@fp/ui-components';

const renderWithTheme = (ui: React.ReactElement) => {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
};

describe('GPSFieldWithMapAssist', () => {
  describe('exports', () => {
    it('exports GPSFieldWithMapAssist component', () => {
      expect(GPSFieldWithMapAssist).toBeDefined();
      expect(typeof GPSFieldWithMapAssist).toBe('function');
    });

    it('exports GPSCoordinates type (verified via TypeScript)', () => {
      const coords: GPSCoordinates = {
        lat: -1.2921,
        lng: 36.8219,
      };
      expect(coords.lat).toBe(-1.2921);
    });

    it('exports GPSFieldWithMapAssistProps type (verified via TypeScript)', () => {
      const props: GPSFieldWithMapAssistProps = {
        value: { lat: null, lng: null },
        onChange: vi.fn(),
      };
      expect(props.value.lat).toBeNull();
    });
  });

  describe('rendering', () => {
    it('renders latitude and longitude fields', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
        />
      );

      expect(screen.getByLabelText(/latitude/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/longitude/i)).toBeInTheDocument();
    });

    it('renders with existing coordinates', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: -1.2921, lng: 36.8219 }}
          onChange={handleChange}
        />
      );

      const latInput = screen.getByLabelText(/latitude/i) as HTMLInputElement;
      const lngInput = screen.getByLabelText(/longitude/i) as HTMLInputElement;

      expect(latInput.value).toBe('-1.2921');
      expect(lngInput.value).toBe('36.8219');
    });

    it('renders map toggle button', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
        />
      );

      expect(screen.getByLabelText(/show map/i)).toBeInTheDocument();
    });

    it('renders get location button', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
        />
      );

      expect(screen.getByLabelText(/get current location/i)).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onChange when latitude is entered', async () => {
      const user = userEvent.setup();
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
        />
      );

      const latInput = screen.getByLabelText(/latitude/i);
      await user.clear(latInput);
      await user.type(latInput, '-1.5');

      expect(handleChange).toHaveBeenCalled();
    });

    it('calls onChange when longitude is entered', async () => {
      const user = userEvent.setup();
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
        />
      );

      const lngInput = screen.getByLabelText(/longitude/i);
      await user.clear(lngInput);
      await user.type(lngInput, '36.5');

      expect(handleChange).toHaveBeenCalled();
    });

    it('toggles map visibility when button is clicked', async () => {
      const user = userEvent.setup();
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
        />
      );

      const toggleButton = screen.getByLabelText(/show map/i);
      await user.click(toggleButton);

      // Map should be visible
      expect(screen.getByTestId('map-container')).toBeInTheDocument();

      // Button label should change to hide
      expect(screen.getByLabelText(/hide map/i)).toBeInTheDocument();
    });
  });

  describe('props', () => {
    it('shows error state for latitude', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
          errors={{ lat: 'Latitude is required' }}
        />
      );

      expect(screen.getByText('Latitude is required')).toBeInTheDocument();
    });

    it('shows error state for longitude', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
          errors={{ lng: 'Longitude is required' }}
        />
      );

      expect(screen.getByText('Longitude is required')).toBeInTheDocument();
    });

    it('disables fields when disabled prop is true', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
          disabled
        />
      );

      expect(screen.getByLabelText(/latitude/i)).toBeDisabled();
      expect(screen.getByLabelText(/longitude/i)).toBeDisabled();
    });

    it('shows helper text', () => {
      const handleChange = vi.fn();

      renderWithTheme(
        <GPSFieldWithMapAssist
          value={{ lat: null, lng: null }}
          onChange={handleChange}
          helperText="Enter farm coordinates"
        />
      );

      expect(screen.getByText('Enter farm coordinates')).toBeInTheDocument();
    });
  });
});
