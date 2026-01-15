import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { ThemeProvider } from '../../theme';
import {
  GPSFieldWithMapAssist,
  GPSCoordinates,
} from './GPSFieldWithMapAssist';

/**
 * GPSFieldWithMapAssist provides coordinate input fields with map assistance.
 *
 * **Required CSS imports in your application:**
 * ```tsx
 * import 'leaflet/dist/leaflet.css';
 * ```
 *
 * Features:
 * - Latitude/Longitude text input fields
 * - Collapsible map picker with click-to-select
 * - "Get current location" button (uses browser geolocation)
 * - Two-way binding between fields and map
 */
const meta: Meta<typeof GPSFieldWithMapAssist> = {
  title: 'Map Components/GPSFieldWithMapAssist',
  component: GPSFieldWithMapAssist,
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
          'Lat/Lng text fields with collapsible map picker for GPS coordinate input.',
      },
    },
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof GPSFieldWithMapAssist>;

/**
 * Default story component.
 */
function DefaultStory(): JSX.Element {
  const [coords, setCoords] = useState<GPSCoordinates>({
    lat: null,
    lng: null,
  });

  return (
    <div style={{ maxWidth: '500px' }}>
      <GPSFieldWithMapAssist value={coords} onChange={setCoords} />
      <pre style={{ marginTop: '16px', fontSize: '12px' }}>
        Value: {JSON.stringify(coords, null, 2)}
      </pre>
    </div>
  );
}

/**
 * Default GPS field with no initial coordinates.
 * Click the map icon to expand the map picker.
 */
export const Default: Story = {
  render: () => <DefaultStory />,
};

/**
 * With initial value story component.
 */
function WithInitialValueStory(): JSX.Element {
  const [coords, setCoords] = useState<GPSCoordinates>({
    lat: -0.4167,
    lng: 36.95,
  });

  return (
    <div style={{ maxWidth: '500px' }}>
      <GPSFieldWithMapAssist value={coords} onChange={setCoords} />
    </div>
  );
}

/**
 * GPS field with initial coordinates.
 * The map will center on the provided location.
 */
export const WithInitialValue: Story = {
  render: () => <WithInitialValueStory />,
};

/**
 * Required story component.
 */
function RequiredStory(): JSX.Element {
  const [coords, setCoords] = useState<GPSCoordinates>({
    lat: null,
    lng: null,
  });

  return (
    <div style={{ maxWidth: '500px' }}>
      <GPSFieldWithMapAssist
        value={coords}
        onChange={setCoords}
        required
        helperText="Click the map icon for visual selection"
      />
    </div>
  );
}

/**
 * GPS field marked as required.
 */
export const Required: Story = {
  render: () => <RequiredStory />,
};

/**
 * With errors story component.
 */
function WithErrorsStory(): JSX.Element {
  const [coords, setCoords] = useState<GPSCoordinates>({
    lat: 95, // Invalid latitude
    lng: 200, // Invalid longitude
  });

  return (
    <div style={{ maxWidth: '500px' }}>
      <GPSFieldWithMapAssist
        value={coords}
        onChange={setCoords}
        errors={{
          lat: 'Latitude must be between -90 and 90',
          lng: 'Longitude must be between -180 and 180',
        }}
      />
    </div>
  );
}

/**
 * GPS field with validation errors.
 */
export const WithErrors: Story = {
  render: () => <WithErrorsStory />,
};

/**
 * Disabled story component.
 */
function DisabledStory(): JSX.Element {
  const [coords, setCoords] = useState<GPSCoordinates>({
    lat: -0.4167,
    lng: 36.95,
  });

  return (
    <div style={{ maxWidth: '500px' }}>
      <GPSFieldWithMapAssist value={coords} onChange={setCoords} disabled />
    </div>
  );
}

/**
 * Disabled GPS field.
 */
export const Disabled: Story = {
  render: () => <DisabledStory />,
};

/**
 * Custom labels story component.
 */
function CustomLabelsStory(): JSX.Element {
  const [coords, setCoords] = useState<GPSCoordinates>({
    lat: null,
    lng: null,
  });

  return (
    <div style={{ maxWidth: '500px' }}>
      <GPSFieldWithMapAssist
        value={coords}
        onChange={setCoords}
        latLabel="Farm Latitude"
        lngLabel="Farm Longitude"
        helperText="Enter the GPS coordinates of the farm"
      />
    </div>
  );
}

/**
 * GPS field with custom labels.
 */
export const CustomLabels: Story = {
  render: () => <CustomLabelsStory />,
};

/**
 * Custom default center story component.
 */
function CustomDefaultCenterStory(): JSX.Element {
  const [coords, setCoords] = useState<GPSCoordinates>({
    lat: null,
    lng: null,
  });

  return (
    <div style={{ maxWidth: '500px' }}>
      <GPSFieldWithMapAssist
        value={coords}
        onChange={setCoords}
        defaultCenter={{ lat: 0.05, lng: 37.65 }}
        helperText="Default map center: Meru, Kenya"
      />
    </div>
  );
}

/**
 * GPS field with custom default center (Meru, Kenya).
 */
export const CustomDefaultCenter: Story = {
  render: () => <CustomDefaultCenterStory />,
};
