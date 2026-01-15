import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { Box, Typography, Chip } from '@mui/material';
import { MapDisplay } from './MapDisplay';

// Note: Storybook preview loads leaflet CSS via preview-head.html

const meta: Meta<typeof MapDisplay> = {
  component: MapDisplay,
  title: 'Maps/MapDisplay',
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof MapDisplay>;

const kenyaFactories = [
  { id: 'nyeri', lat: -0.4167, lng: 36.95, title: 'Nyeri Tea Factory' },
  { id: 'meru', lat: -0.0236, lng: 37.6497, title: 'Meru Tea Factory' },
  { id: 'kiambu', lat: -1.1714, lng: 36.8356, title: 'Kiambu Tea Factory' },
  { id: 'kericho', lat: -0.3689, lng: 35.2863, title: 'Kericho Tea Factory' },
];

/** Basic map with default center (Nairobi) */
export const Default: Story = {
  args: {
    height: 400,
  },
};

/** Map with markers */
export const WithMarkers: Story = {
  args: {
    markers: kenyaFactories,
    fitBounds: true,
    height: 400,
  },
};

/** Map with clickable markers */
export const ClickableMarkers: Story = {
  args: {
    markers: kenyaFactories,
    fitBounds: true,
    height: 400,
    onMarkerClick: fn(),
  },
};

/** Single marker centered */
export const SingleMarker: Story = {
  args: {
    markers: [{ id: 'nyeri', lat: -0.4167, lng: 36.95, title: 'Nyeri Tea Factory' }],
    centerLat: -0.4167,
    centerLng: 36.95,
    zoom: 12,
    height: 400,
  },
};

/** With custom popup content */
export const CustomPopups: Story = {
  args: {
    markers: [
      {
        id: 'nyeri',
        lat: -0.4167,
        lng: 36.95,
        title: 'Nyeri Tea Factory',
        popupContent: (
          <Box sx={{ minWidth: 150 }}>
            <Typography variant="subtitle2">Nyeri Tea Factory</Typography>
            <Typography variant="body2" color="text.secondary">
              Collection Points: 12
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Active Farmers: 342
            </Typography>
            <Chip label="Active" color="success" size="small" sx={{ mt: 1 }} />
          </Box>
        ),
      },
      {
        id: 'meru',
        lat: -0.0236,
        lng: 37.6497,
        title: 'Meru Tea Factory',
        popupContent: (
          <Box sx={{ minWidth: 150 }}>
            <Typography variant="subtitle2">Meru Tea Factory</Typography>
            <Typography variant="body2" color="text.secondary">
              Collection Points: 8
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Active Farmers: 215
            </Typography>
            <Chip label="Active" color="success" size="small" sx={{ mt: 1 }} />
          </Box>
        ),
      },
    ],
    fitBounds: true,
    height: 400,
  },
};

/** Small map (e.g., for cards) */
export const SmallMap: Story = {
  args: {
    markers: [{ id: 'nyeri', lat: -0.4167, lng: 36.95, title: 'Nyeri' }],
    centerLat: -0.4167,
    centerLng: 36.95,
    zoom: 11,
    height: 200,
  },
};

/** Full width map */
export const FullWidth: Story = {
  args: {
    markers: kenyaFactories,
    fitBounds: true,
    height: 500,
  },
  decorators: [
    (Story) => (
      <Box sx={{ width: '100%' }}>
        <Story />
      </Box>
    ),
  ],
};

/** Empty map (no markers) */
export const EmptyMap: Story = {
  args: {
    centerLat: -1.2921,
    centerLng: 36.8219,
    zoom: 7,
    height: 400,
  },
};
