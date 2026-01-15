import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { ThemeProvider } from '../../theme';
import { BoundaryDrawer, GeoJSONPolygon, BoundaryStats } from './BoundaryDrawer';

/**
 * BoundaryDrawer provides polygon drawing for region boundaries using Leaflet.draw.
 *
 * **Required CSS imports in your application:**
 * ```tsx
 * import 'leaflet/dist/leaflet.css';
 * import 'leaflet-draw/dist/leaflet.draw.css';
 * ```
 *
 * Features:
 * - Draw polygons using the polygon tool
 * - Edit existing boundaries
 * - Delete boundaries
 * - View area, perimeter, and centroid statistics
 * - Display existing markers (e.g., collection points)
 */
const meta: Meta<typeof BoundaryDrawer> = {
  title: 'Map Components/BoundaryDrawer',
  component: BoundaryDrawer,
  decorators: [
    (Story) => (
      <ThemeProvider>
        <Story />
      </ThemeProvider>
    ),
  ],
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component:
          'Leaflet.draw polygon drawing component with area/perimeter statistics.',
      },
    },
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof BoundaryDrawer>;

// Sample boundary for Nyeri region in Kenya
const sampleNyeriBoundary: GeoJSONPolygon = {
  type: 'Polygon',
  coordinates: [
    [
      [36.95, -0.4],
      [37.05, -0.4],
      [37.05, -0.5],
      [36.95, -0.5],
      [36.95, -0.4],
    ],
  ],
};

// Sample markers (collection points)
const sampleMarkers = [
  { id: 'cp-1', lat: -0.42, lng: 36.97, title: 'Collection Point A' },
  { id: 'cp-2', lat: -0.45, lng: 37.01, title: 'Collection Point B' },
  { id: 'cp-3', lat: -0.48, lng: 36.99, title: 'Collection Point C' },
];

/**
 * Default story render component.
 */
function DefaultStory(): JSX.Element {
  const [boundary, setBoundary] = useState<GeoJSONPolygon | null>(null);
  const [stats, setStats] = useState<BoundaryStats | null>(null);

  return (
    <div>
      <BoundaryDrawer
        onBoundaryChange={(b, s) => {
          setBoundary(b);
          setStats(s);
        }}
        defaultCenter={{ lat: -0.45, lng: 36.98 }}
        defaultZoom={11}
      />
      {boundary && (
        <pre style={{ marginTop: '16px', fontSize: '12px' }}>
          {JSON.stringify({ boundary, stats }, null, 2)}
        </pre>
      )}
    </div>
  );
}

/**
 * Default boundary drawer without existing boundary.
 * Use the polygon tool in the top-right to draw a region.
 */
export const Default: Story = {
  render: () => <DefaultStory />,
};

/**
 * Existing boundary story render component.
 */
function WithExistingBoundaryStory(): JSX.Element {
  const [boundary, setBoundary] = useState<GeoJSONPolygon | null>(
    sampleNyeriBoundary
  );
  const [stats, setStats] = useState<BoundaryStats | null>(null);

  return (
    <div>
      <BoundaryDrawer
        existingBoundary={boundary ?? undefined}
        onBoundaryChange={(b, s) => {
          setBoundary(b);
          setStats(s);
        }}
      />
      {stats && (
        <pre style={{ marginTop: '16px', fontSize: '12px' }}>
          Stats: {JSON.stringify(stats, null, 2)}
        </pre>
      )}
    </div>
  );
}

/**
 * Boundary drawer with an existing boundary loaded.
 * The boundary can be edited or deleted.
 */
export const WithExistingBoundary: Story = {
  render: () => <WithExistingBoundaryStory />,
};

/**
 * Markers story render component.
 */
function WithMarkersStory(): JSX.Element {
  const [boundary, setBoundary] = useState<GeoJSONPolygon | null>(
    sampleNyeriBoundary
  );

  return (
    <BoundaryDrawer
      existingBoundary={boundary ?? undefined}
      existingMarkers={sampleMarkers}
      onBoundaryChange={(b) => setBoundary(b)}
    />
  );
}

/**
 * Boundary drawer with existing markers (collection points).
 * Markers are displayed but not editable.
 */
export const WithMarkers: Story = {
  render: () => <WithMarkersStory />,
};

/**
 * Disabled boundary drawer (read-only mode).
 * Drawing and editing controls are hidden.
 */
export const Disabled: Story = {
  render: () => (
    <BoundaryDrawer
      existingBoundary={sampleNyeriBoundary}
      existingMarkers={sampleMarkers}
      onBoundaryChange={() => {}}
      disabled
    />
  ),
};

/**
 * Custom height story render component.
 */
function CustomHeightStory(): JSX.Element {
  const [, setBoundary] = useState<GeoJSONPolygon | null>(null);

  return (
    <BoundaryDrawer
      onBoundaryChange={(b) => setBoundary(b)}
      height={300}
      defaultCenter={{ lat: -0.45, lng: 36.98 }}
      defaultZoom={10}
    />
  );
}

/**
 * Custom height boundary drawer.
 */
export const CustomHeight: Story = {
  render: () => <CustomHeightStory />,
};
