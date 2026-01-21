/**
 * Region Create Page
 *
 * Form for creating a new region with geography, weather config, and calendar.
 * Implements Story 9.2 - Region Management.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Box,
  Alert,
  Paper,
  Grid2 as Grid,
  TextField,
  MenuItem,
  FormControlLabel,
  Switch,
  Typography,
  Button,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SaveIcon from '@mui/icons-material/Save';
import { PageHeader, BoundaryDrawer, type GeoJSONPolygon, type BoundaryStats } from '@fp/ui-components';
import {
  createRegion,
  geoJSONToRegionBoundary,
  type AltitudeBand,
  type RegionCreateRequest,
} from '@/api';

// ============================================================================
// Validation Schema
// ============================================================================

const mmddPattern = /^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;
const timePattern = /^([01]\d|2[0-3]):([0-5]\d)$/;
const timeRangePattern = /^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$/;

const regionFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  county: z.string().min(1, 'County is required').max(50),
  country: z.string().max(50).default('Kenya'),
  altitude_band: z.enum(['highland', 'midland', 'lowland']),
  center_lat: z.coerce.number().min(-90).max(90),
  center_lng: z.coerce.number().min(-180).max(180),
  radius_km: z.coerce.number().min(0.1).max(100),
  altitude_min: z.coerce.number().min(0),
  altitude_max: z.coerce.number().min(0),
  weather_api_lat: z.coerce.number().min(-90).max(90),
  weather_api_lng: z.coerce.number().min(-180).max(180),
  weather_api_altitude: z.coerce.number().min(0),
  weather_collection_time: z.string().regex(timePattern, 'Format: HH:MM'),
  first_flush_start: z.string().regex(mmddPattern, 'Format: MM-DD'),
  first_flush_end: z.string().regex(mmddPattern, 'Format: MM-DD'),
  first_flush_characteristics: z.string().max(200).optional(),
  monsoon_flush_start: z.string().regex(mmddPattern, 'Format: MM-DD'),
  monsoon_flush_end: z.string().regex(mmddPattern, 'Format: MM-DD'),
  monsoon_flush_characteristics: z.string().max(200).optional(),
  autumn_flush_start: z.string().regex(mmddPattern, 'Format: MM-DD'),
  autumn_flush_end: z.string().regex(mmddPattern, 'Format: MM-DD'),
  autumn_flush_characteristics: z.string().max(200).optional(),
  dormant_start: z.string().regex(mmddPattern, 'Format: MM-DD'),
  dormant_end: z.string().regex(mmddPattern, 'Format: MM-DD'),
  dormant_characteristics: z.string().max(200).optional(),
  soil_type: z.string().min(1, 'Soil type is required').max(50),
  typical_diseases: z.string().max(500),
  harvest_peak_hours: z.string().regex(timeRangePattern, 'Format: HH:MM-HH:MM'),
  frost_risk: z.boolean(),
}).refine((data) => data.altitude_min < data.altitude_max, {
  message: 'Min altitude must be less than max altitude',
  path: ['altitude_max'],
});

type FormValues = z.infer<typeof regionFormSchema>;

// ============================================================================
// Default Values
// ============================================================================

const DEFAULT_VALUES: FormValues = {
  name: '',
  county: '',
  country: 'Kenya',
  altitude_band: 'highland',
  center_lat: -1.0,
  center_lng: 37.0,
  radius_km: 15,
  altitude_min: 1800,
  altitude_max: 2500,
  weather_api_lat: -1.0,
  weather_api_lng: 37.0,
  weather_api_altitude: 2000,
  weather_collection_time: '06:00',
  first_flush_start: '03-15',
  first_flush_end: '06-15',
  first_flush_characteristics: 'High quality spring tea',
  monsoon_flush_start: '06-16',
  monsoon_flush_end: '09-30',
  monsoon_flush_characteristics: 'High volume production',
  autumn_flush_start: '10-01',
  autumn_flush_end: '12-15',
  autumn_flush_characteristics: 'Balanced quality',
  dormant_start: '12-16',
  dormant_end: '03-14',
  dormant_characteristics: 'Minimal growth',
  soil_type: 'volcanic_red',
  typical_diseases: '',
  harvest_peak_hours: '06:00-10:00',
  frost_risk: false,
};

// ============================================================================
// Component
// ============================================================================

export function RegionCreate(): JSX.Element {
  const navigate = useNavigate();

  // Form state
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(regionFormSchema),
    defaultValues: DEFAULT_VALUES,
  });

  // Boundary state (managed separately from form)
  const [boundary, setBoundary] = useState<GeoJSONPolygon | null>(null);
  const [boundaryStats, setBoundaryStats] = useState<BoundaryStats | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Watch center GPS for map default
  const centerLat = watch('center_lat');
  const centerLng = watch('center_lng');

  // Handle boundary changes
  const handleBoundaryChange = (newBoundary: GeoJSONPolygon | null, stats: BoundaryStats | null) => {
    setBoundary(newBoundary);
    setBoundaryStats(stats);

    // Auto-update center if boundary centroid is available
    if (stats?.centroid) {
      setValue('center_lat', stats.centroid.lat);
      setValue('center_lng', stats.centroid.lng);
      setValue('weather_api_lat', stats.centroid.lat);
      setValue('weather_api_lng', stats.centroid.lng);
    }

    // Auto-calculate radius from polygon area (equivalent circle radius)
    if (stats?.areaKm2) {
      const equivalentRadius = Math.sqrt(stats.areaKm2 / Math.PI);
      setValue('radius_km', Math.round(equivalentRadius * 10) / 10); // Round to 1 decimal
    }
  };

  // Form submission
  const onSubmit = async (data: FormValues) => {
    setSubmitError(null);

    try {
      const request: RegionCreateRequest = {
        name: data.name,
        county: data.county,
        country: data.country,
        geography: {
          center_gps: { lat: data.center_lat, lng: data.center_lng },
          radius_km: data.radius_km,
          altitude_band: {
            min_meters: data.altitude_min,
            max_meters: data.altitude_max,
            label: data.altitude_band as AltitudeBand,
          },
          boundary: geoJSONToRegionBoundary(boundary),
          area_km2: boundaryStats?.areaKm2,
          perimeter_km: boundaryStats?.perimeterKm,
        },
        flush_calendar: {
          first_flush: {
            start: data.first_flush_start,
            end: data.first_flush_end,
            characteristics: data.first_flush_characteristics,
          },
          monsoon_flush: {
            start: data.monsoon_flush_start,
            end: data.monsoon_flush_end,
            characteristics: data.monsoon_flush_characteristics,
          },
          autumn_flush: {
            start: data.autumn_flush_start,
            end: data.autumn_flush_end,
            characteristics: data.autumn_flush_characteristics,
          },
          dormant: {
            start: data.dormant_start,
            end: data.dormant_end,
            characteristics: data.dormant_characteristics,
          },
        },
        agronomic: {
          soil_type: data.soil_type,
          typical_diseases: data.typical_diseases.split(',').map((d) => d.trim()).filter(Boolean),
          harvest_peak_hours: data.harvest_peak_hours,
          frost_risk: data.frost_risk,
        },
        weather_config: {
          api_location: { lat: data.weather_api_lat, lng: data.weather_api_lng },
          altitude_for_api: data.weather_api_altitude,
          collection_time: data.weather_collection_time,
        },
      };

      const created = await createRegion(request);
      navigate(`/regions/${created.id}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create region');
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <PageHeader
        title="Create Region"
        subtitle="Add a new geographic region with configuration"
        onBack={() => navigate('/regions')}
        actions={[
          {
            id: 'save',
            label: isSubmitting ? 'Saving...' : 'Save Region',
            icon: isSubmitting ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />,
            variant: 'contained',
            onClick: handleSubmit(onSubmit),
            disabled: isSubmitting,
          },
        ]}
      />

      {submitError && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setSubmitError(null)}>
          {submitError}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Basic Information */}
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Basic Information
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="name"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Region Name"
                      fullWidth
                      required
                      error={!!errors.name}
                      helperText={errors.name?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="county"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="County"
                      fullWidth
                      required
                      error={!!errors.county}
                      helperText={errors.county?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="country"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Country"
                      fullWidth
                      error={!!errors.country}
                      helperText={errors.country?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="altitude_band"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Altitude Band"
                      fullWidth
                      required
                      error={!!errors.altitude_band}
                      helperText={errors.altitude_band?.message}
                    >
                      <MenuItem value="highland">Highland (1800m+)</MenuItem>
                      <MenuItem value="midland">Midland (1400-1800m)</MenuItem>
                      <MenuItem value="lowland">Lowland (&lt;1400m)</MenuItem>
                    </TextField>
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Map and Boundary */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Region Boundary
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Draw a polygon to define the precise region boundary. Use the polygon tool in the top-right corner.
            </Typography>
            <BoundaryDrawer
              existingBoundary={boundary ?? undefined}
              onBoundaryChange={handleBoundaryChange}
              defaultCenter={{ lat: centerLat, lng: centerLng }}
              defaultZoom={10}
              height={400}
            />
          </Paper>
        </Grid>

        {/* Geography Details */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Geography
            </Typography>
            <Grid container spacing={2}>
              <Grid size={6}>
                <Controller
                  name="center_lat"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Center Lat"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.center_lat}
                      helperText={errors.center_lat?.message}
                      inputProps={{ step: 0.0001 }}
                    />
                  )}
                />
              </Grid>
              <Grid size={6}>
                <Controller
                  name="center_lng"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Center Lng"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.center_lng}
                      helperText={errors.center_lng?.message}
                      inputProps={{ step: 0.0001 }}
                    />
                  )}
                />
              </Grid>
              <Grid size={12}>
                <Controller
                  name="radius_km"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Radius (km)"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.radius_km}
                      helperText={errors.radius_km?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={6}>
                <Controller
                  name="altitude_min"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Min Altitude (m)"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.altitude_min}
                      helperText={errors.altitude_min?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={6}>
                <Controller
                  name="altitude_max"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Max Altitude (m)"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.altitude_max}
                      helperText={errors.altitude_max?.message}
                    />
                  )}
                />
              </Grid>
            </Grid>

            <Typography variant="h6" sx={{ mt: 3 }} gutterBottom>
              Weather API Config
            </Typography>
            <Grid container spacing={2}>
              <Grid size={6}>
                <Controller
                  name="weather_api_lat"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="API Lat"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.weather_api_lat}
                      helperText={errors.weather_api_lat?.message}
                      inputProps={{ step: 0.0001 }}
                    />
                  )}
                />
              </Grid>
              <Grid size={6}>
                <Controller
                  name="weather_api_lng"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="API Lng"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.weather_api_lng}
                      helperText={errors.weather_api_lng?.message}
                      inputProps={{ step: 0.0001 }}
                    />
                  )}
                />
              </Grid>
              <Grid size={6}>
                <Controller
                  name="weather_api_altitude"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="API Altitude (m)"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.weather_api_altitude}
                      helperText={errors.weather_api_altitude?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={6}>
                <Controller
                  name="weather_collection_time"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Collection Time"
                      fullWidth
                      required
                      placeholder="HH:MM"
                      error={!!errors.weather_collection_time}
                      helperText={errors.weather_collection_time?.message || 'e.g., 06:00'}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Flush Calendar */}
        <Grid size={12}>
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Flush Calendar</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={3}>
                {/* First Flush */}
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Typography variant="subtitle2" color="success.main" gutterBottom>
                    First Flush (Spring)
                  </Typography>
                  <Grid container spacing={1}>
                    <Grid size={6}>
                      <Controller
                        name="first_flush_start"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Start"
                            size="small"
                            fullWidth
                            placeholder="MM-DD"
                            error={!!errors.first_flush_start}
                            helperText={errors.first_flush_start?.message}
                          />
                        )}
                      />
                    </Grid>
                    <Grid size={6}>
                      <Controller
                        name="first_flush_end"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="End"
                            size="small"
                            fullWidth
                            placeholder="MM-DD"
                            error={!!errors.first_flush_end}
                            helperText={errors.first_flush_end?.message}
                          />
                        )}
                      />
                    </Grid>
                    <Grid size={12}>
                      <Controller
                        name="first_flush_characteristics"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Characteristics"
                            size="small"
                            fullWidth
                            multiline
                            rows={2}
                          />
                        )}
                      />
                    </Grid>
                  </Grid>
                </Grid>

                {/* Monsoon Flush */}
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Typography variant="subtitle2" color="info.main" gutterBottom>
                    Monsoon Flush
                  </Typography>
                  <Grid container spacing={1}>
                    <Grid size={6}>
                      <Controller
                        name="monsoon_flush_start"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Start"
                            size="small"
                            fullWidth
                            placeholder="MM-DD"
                            error={!!errors.monsoon_flush_start}
                            helperText={errors.monsoon_flush_start?.message}
                          />
                        )}
                      />
                    </Grid>
                    <Grid size={6}>
                      <Controller
                        name="monsoon_flush_end"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="End"
                            size="small"
                            fullWidth
                            placeholder="MM-DD"
                            error={!!errors.monsoon_flush_end}
                            helperText={errors.monsoon_flush_end?.message}
                          />
                        )}
                      />
                    </Grid>
                    <Grid size={12}>
                      <Controller
                        name="monsoon_flush_characteristics"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Characteristics"
                            size="small"
                            fullWidth
                            multiline
                            rows={2}
                          />
                        )}
                      />
                    </Grid>
                  </Grid>
                </Grid>

                {/* Autumn Flush */}
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Typography variant="subtitle2" color="warning.main" gutterBottom>
                    Autumn Flush
                  </Typography>
                  <Grid container spacing={1}>
                    <Grid size={6}>
                      <Controller
                        name="autumn_flush_start"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Start"
                            size="small"
                            fullWidth
                            placeholder="MM-DD"
                            error={!!errors.autumn_flush_start}
                            helperText={errors.autumn_flush_start?.message}
                          />
                        )}
                      />
                    </Grid>
                    <Grid size={6}>
                      <Controller
                        name="autumn_flush_end"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="End"
                            size="small"
                            fullWidth
                            placeholder="MM-DD"
                            error={!!errors.autumn_flush_end}
                            helperText={errors.autumn_flush_end?.message}
                          />
                        )}
                      />
                    </Grid>
                    <Grid size={12}>
                      <Controller
                        name="autumn_flush_characteristics"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Characteristics"
                            size="small"
                            fullWidth
                            multiline
                            rows={2}
                          />
                        )}
                      />
                    </Grid>
                  </Grid>
                </Grid>

                {/* Dormant */}
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Dormant (Winter)
                  </Typography>
                  <Grid container spacing={1}>
                    <Grid size={6}>
                      <Controller
                        name="dormant_start"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Start"
                            size="small"
                            fullWidth
                            placeholder="MM-DD"
                            error={!!errors.dormant_start}
                            helperText={errors.dormant_start?.message}
                          />
                        )}
                      />
                    </Grid>
                    <Grid size={6}>
                      <Controller
                        name="dormant_end"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="End"
                            size="small"
                            fullWidth
                            placeholder="MM-DD"
                            error={!!errors.dormant_end}
                            helperText={errors.dormant_end?.message}
                          />
                        )}
                      />
                    </Grid>
                    <Grid size={12}>
                      <Controller
                        name="dormant_characteristics"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Characteristics"
                            size="small"
                            fullWidth
                            multiline
                            rows={2}
                          />
                        )}
                      />
                    </Grid>
                  </Grid>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>

        {/* Agronomic Factors */}
        <Grid size={12}>
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Agronomic Factors</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Controller
                    name="soil_type"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Soil Type"
                        fullWidth
                        required
                        error={!!errors.soil_type}
                        helperText={errors.soil_type?.message || 'e.g., volcanic_red'}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Controller
                    name="harvest_peak_hours"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Harvest Peak Hours"
                        fullWidth
                        required
                        placeholder="HH:MM-HH:MM"
                        error={!!errors.harvest_peak_hours}
                        helperText={errors.harvest_peak_hours?.message || 'e.g., 06:00-10:00'}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Controller
                    name="typical_diseases"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Typical Diseases"
                        fullWidth
                        placeholder="comma-separated"
                        error={!!errors.typical_diseases}
                        helperText={errors.typical_diseases?.message || 'e.g., blister_blight, red_rust'}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Controller
                    name="frost_risk"
                    control={control}
                    render={({ field }) => (
                      <FormControlLabel
                        control={
                          <Switch
                            checked={field.value}
                            onChange={(e) => field.onChange(e.target.checked)}
                          />
                        }
                        label="Frost Risk"
                      />
                    )}
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>

        {/* Submit Button (mobile) */}
        <Grid size={12}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            <Button variant="outlined" onClick={() => navigate('/regions')}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              startIcon={isSubmitting ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving...' : 'Save Region'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}
