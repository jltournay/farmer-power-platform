/**
 * Region Detail Page
 *
 * Displays full region information with map, weather config, and calendar.
 * Implements Story 9.2 - Region Management.
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Alert,
  CircularProgress,
  Paper,
  Grid2 as Grid,
  Typography,
  Chip,
  Divider,
  Card,
  CardContent,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import PublicIcon from '@mui/icons-material/Public';
import WbSunnyIcon from '@mui/icons-material/WbSunny';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import GrassIcon from '@mui/icons-material/Grass';
import { PageHeader, BoundaryDrawer, type GeoJSONPolygon, type BoundaryStats } from '@fp/ui-components';
import { getRegion, regionBoundaryToGeoJSON, type RegionDetail as RegionDetailType } from '@/api';

/**
 * Format date from MM-DD to readable format.
 */
function formatDate(date: string): string {
  const [month, day] = date.split('-');
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[parseInt(month, 10) - 1]} ${parseInt(day, 10)}`;
}

/**
 * Section card component for consistent styling.
 */
interface SectionCardProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}

function SectionCard({ title, icon, children }: SectionCardProps): JSX.Element {
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          {icon}
          <Typography variant="h6" component="h2">
            {title}
          </Typography>
        </Box>
        {children}
      </CardContent>
    </Card>
  );
}

/**
 * Info row component for key-value display.
 */
interface InfoRowProps {
  label: string;
  value: React.ReactNode;
}

function InfoRow({ label, value }: InfoRowProps): JSX.Element {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" fontWeight={500}>
        {value}
      </Typography>
    </Box>
  );
}

/**
 * Region detail page component.
 */
export function RegionDetail(): JSX.Element {
  const { regionId } = useParams<{ regionId: string }>();
  const navigate = useNavigate();

  // State
  const [region, setRegion] = useState<RegionDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data fetching
  const fetchData = useCallback(async () => {
    if (!regionId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getRegion(regionId);
      setRegion(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load region');
    } finally {
      setLoading(false);
    }
  }, [regionId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Convert region boundary to GeoJSON format for BoundaryDrawer
  const existingBoundary = regionBoundaryToGeoJSON(region?.geography.boundary);

  // Dummy handler for read-only mode
  const handleBoundaryChange = (_boundary: GeoJSONPolygon | null, _stats: BoundaryStats | null) => {
    // Read-only - no changes
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <PageHeader
          title="Region"
          onBack={() => navigate('/regions')}
        />
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!region) {
    return (
      <Box>
        <PageHeader
          title="Region"
          onBack={() => navigate('/regions')}
        />
        <Alert severity="warning">Region not found</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title={region.name}
        subtitle={`${region.county}, ${region.country}`}
        onBack={() => navigate('/regions')}
        statusBadge={
          <Chip
            label={region.is_active ? 'Active' : 'Inactive'}
            color={region.is_active ? 'success' : 'default'}
            size="small"
          />
        }
        actions={[
          {
            id: 'edit',
            label: 'Edit Region',
            icon: <EditIcon />,
            variant: 'contained',
            onClick: () => navigate(`/regions/${regionId}/edit`),
          },
        ]}
      />

      <Grid container spacing={3}>
        {/* Left Column - Map */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Region Boundary
            </Typography>
            <BoundaryDrawer
              existingBoundary={existingBoundary}
              onBoundaryChange={handleBoundaryChange}
              defaultCenter={{
                lat: region.geography.center_gps.lat,
                lng: region.geography.center_gps.lng,
              }}
              defaultZoom={10}
              disabled={true}
              height={450}
            />
          </Paper>
        </Grid>

        {/* Right Column - Details */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Geography */}
            <SectionCard title="Geography" icon={<PublicIcon color="primary" />}>
              <InfoRow
                label="Altitude Band"
                value={
                  <Chip
                    label={region.geography.altitude_band.label}
                    size="small"
                    color={
                      region.geography.altitude_band.label === 'highland'
                        ? 'success'
                        : region.geography.altitude_band.label === 'midland'
                          ? 'warning'
                          : 'info'
                    }
                  />
                }
              />
              <InfoRow
                label="Altitude Range"
                value={`${region.geography.altitude_band.min_meters}m - ${region.geography.altitude_band.max_meters}m`}
              />
              <InfoRow
                label="Center GPS"
                value={`${region.geography.center_gps.lat.toFixed(4)}, ${region.geography.center_gps.lng.toFixed(4)}`}
              />
              <InfoRow label="Radius" value={`${region.geography.radius_km} km`} />
              {region.geography.area_km2 && (
                <InfoRow label="Area" value={`${region.geography.area_km2} km²`} />
              )}
              {region.geography.perimeter_km && (
                <InfoRow label="Perimeter" value={`${region.geography.perimeter_km} km`} />
              )}
              <Divider sx={{ my: 1 }} />
              <InfoRow label="Factories" value={region.factory_count} />
              <InfoRow label="Farmers" value={region.farmer_count} />
            </SectionCard>

            {/* Weather Config */}
            <SectionCard title="Weather Config" icon={<WbSunnyIcon color="primary" />}>
              <InfoRow
                label="API Location"
                value={`${region.weather_config.api_location.lat.toFixed(4)}, ${region.weather_config.api_location.lng.toFixed(4)}`}
              />
              <InfoRow
                label="API Altitude"
                value={`${region.weather_config.altitude_for_api}m`}
              />
              <InfoRow
                label="Collection Time"
                value={region.weather_config.collection_time}
              />
            </SectionCard>
          </Box>
        </Grid>

        {/* Flush Calendar */}
        <Grid size={12}>
          <SectionCard title="Flush Calendar" icon={<CalendarMonthIcon color="primary" />}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="success.main" gutterBottom>
                    First Flush
                  </Typography>
                  <Typography variant="body2">
                    {formatDate(region.flush_calendar.first_flush.start)} - {formatDate(region.flush_calendar.first_flush.end)}
                  </Typography>
                  {region.flush_calendar.first_flush.characteristics && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      {region.flush_calendar.first_flush.characteristics}
                    </Typography>
                  )}
                </Paper>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="info.main" gutterBottom>
                    Monsoon Flush
                  </Typography>
                  <Typography variant="body2">
                    {formatDate(region.flush_calendar.monsoon_flush.start)} - {formatDate(region.flush_calendar.monsoon_flush.end)}
                  </Typography>
                  {region.flush_calendar.monsoon_flush.characteristics && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      {region.flush_calendar.monsoon_flush.characteristics}
                    </Typography>
                  )}
                </Paper>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="warning.main" gutterBottom>
                    Autumn Flush
                  </Typography>
                  <Typography variant="body2">
                    {formatDate(region.flush_calendar.autumn_flush.start)} - {formatDate(region.flush_calendar.autumn_flush.end)}
                  </Typography>
                  {region.flush_calendar.autumn_flush.characteristics && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      {region.flush_calendar.autumn_flush.characteristics}
                    </Typography>
                  )}
                </Paper>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Dormant
                  </Typography>
                  <Typography variant="body2">
                    {formatDate(region.flush_calendar.dormant.start)} - {formatDate(region.flush_calendar.dormant.end)}
                  </Typography>
                  {region.flush_calendar.dormant.characteristics && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      {region.flush_calendar.dormant.characteristics}
                    </Typography>
                  )}
                </Paper>
              </Grid>
            </Grid>
          </SectionCard>
        </Grid>

        {/* Agronomic Factors */}
        <Grid size={12}>
          <SectionCard title="Agronomic Factors" icon={<GrassIcon color="primary" />}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="caption" color="text.secondary">
                  Soil Type
                </Typography>
                <Typography variant="body1">{region.agronomic.soil_type}</Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="caption" color="text.secondary">
                  Harvest Peak Hours
                </Typography>
                <Typography variant="body1">{region.agronomic.harvest_peak_hours}</Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="caption" color="text.secondary">
                  Frost Risk
                </Typography>
                <Typography variant="body1">
                  <Chip
                    label={region.agronomic.frost_risk ? 'Yes' : 'No'}
                    size="small"
                    color={region.agronomic.frost_risk ? 'error' : 'default'}
                  />
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="caption" color="text.secondary">
                  Typical Diseases
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                  {region.agronomic.typical_diseases.length > 0 ? (
                    region.agronomic.typical_diseases.map((disease) => (
                      <Chip key={disease} label={disease} size="small" variant="outlined" />
                    ))
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      None recorded
                    </Typography>
                  )}
                </Box>
              </Grid>
            </Grid>
          </SectionCard>
        </Grid>
      </Grid>
    </Box>
  );
}
