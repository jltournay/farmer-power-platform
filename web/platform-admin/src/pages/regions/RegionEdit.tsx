/**
 * Region Edit Page
 *
 * Form for editing an existing region with geography, weather config, and calendar.
 * Implements Story 9.2 - Region Management.
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  getRegion,
  updateRegion,
  regionBoundaryToGeoJSON,
  geoJSONToRegionBoundary,
  type AltitudeBand,
  type RegionDetail,
  type RegionUpdateRequest,
} from '@/api';

// ============================================================================
// Validation Schema
// ============================================================================

const mmddPattern = /^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;
const timePattern = /^([01]\d|2[0-3]):([0-5]\d)$/;
const timeRangePattern = /^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$/;

const regionFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
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
  is_active: z.boolean(),
}).refine((data) => data.altitude_min < data.altitude_max, {
  message: 'Min altitude must be less than max altitude',
  path: ['altitude_max'],
});

type FormValues = z.infer<typeof regionFormSchema>;

// ============================================================================
// Component
// ============================================================================

export function RegionEdit(): JSX.Element {
  const { regionId } = useParams<{ regionId: string }>();
  const navigate = useNavigate();

  // Loading state
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [region, setRegion] = useState<RegionDetail | null>(null);

  // Form state
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(regionFormSchema),
  });

  // Boundary state (managed separately from form)
  const [boundary, setBoundary] = useState<GeoJSONPolygon | null>(null);
  const [boundaryStats, setBoundaryStats] = useState<BoundaryStats | null>(null);

  // Watch center GPS for map default
  const centerLat = watch('center_lat');
  const centerLng = watch('center_lng');

  // Load region data
  const loadRegion = useCallback(async () => {
    if (!regionId) return;

    setLoading(true);
    setLoadError(null);

    try {
      const data = await getRegion(regionId);
      setRegion(data);

      // Convert boundary
      const geoBoundary = regionBoundaryToGeoJSON(data.geography.boundary);
      setBoundary(geoBoundary ?? null);

      // Set form values
      reset({
        name: data.name,
        altitude_band: data.geography.altitude_band.label,
        center_lat: data.geography.center_gps.lat,
        center_lng: data.geography.center_gps.lng,
        radius_km: data.geography.radius_km,
        altitude_min: data.geography.altitude_band.min_meters,
        altitude_max: data.geography.altitude_band.max_meters,
        weather_api_lat: data.weather_config.api_location.lat,
        weather_api_lng: data.weather_config.api_location.lng,
        weather_api_altitude: data.weather_config.altitude_for_api,
        weather_collection_time: data.weather_config.collection_time,
        first_flush_start: data.flush_calendar.first_flush.start,
        first_flush_end: data.flush_calendar.first_flush.end,
        first_flush_characteristics: data.flush_calendar.first_flush.characteristics ?? '',
        monsoon_flush_start: data.flush_calendar.monsoon_flush.start,
        monsoon_flush_end: data.flush_calendar.monsoon_flush.end,
        monsoon_flush_characteristics: data.flush_calendar.monsoon_flush.characteristics ?? '',
        autumn_flush_start: data.flush_calendar.autumn_flush.start,
        autumn_flush_end: data.flush_calendar.autumn_flush.end,
        autumn_flush_characteristics: data.flush_calendar.autumn_flush.characteristics ?? '',
        dormant_start: data.flush_calendar.dormant.start,
        dormant_end: data.flush_calendar.dormant.end,
        dormant_characteristics: data.flush_calendar.dormant.characteristics ?? '',
        soil_type: data.agronomic.soil_type,
        typical_diseases: data.agronomic.typical_diseases.join(', '),
        harvest_peak_hours: data.agronomic.harvest_peak_hours,
        frost_risk: data.agronomic.frost_risk,
        is_active: data.is_active,
      });
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load region');
    } finally {
      setLoading(false);
    }
  }, [regionId, reset]);

  useEffect(() => {
    loadRegion();
  }, [loadRegion]);

  // Handle boundary changes
  const handleBoundaryChange = (newBoundary: GeoJSONPolygon | null, stats: BoundaryStats | null) => {
    setBoundary(newBoundary);
    setBoundaryStats(stats);

    // Auto-update center if boundary centroid is available
    if (stats?.centroid) {
      setValue('center_lat', stats.centroid.lat);
      setValue('center_lng', stats.centroid.lng);
    }
  };

  // Form submission
  const onSubmit = async (data: FormValues) => {
    if (!regionId) return;

    setSubmitError(null);

    try {
      const request: RegionUpdateRequest = {
        name: data.name,
        is_active: data.is_active,
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

      await updateRegion(regionId, request);
      navigate(`/regions/${regionId}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to update region');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (loadError) {
    return (
      <Box>
        <PageHeader
          title="Edit Region"
          onBack={() => navigate('/regions')}
        />
        <Alert severity="error">{loadError}</Alert>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <PageHeader
        title={`Edit: ${region?.name ?? 'Region'}`}
        subtitle={`${region?.county ?? ''}, ${region?.country ?? ''}`}
        onBack={() => navigate(`/regions/${regionId}`)}
        actions={[
          {
            id: 'save',
            label: isSubmitting ? 'Saving...' : 'Save Changes',
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
              <Grid size={{ xs: 12, sm: 3 }}>
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
              <Grid size={{ xs: 12, sm: 3 }}>
                <Controller
                  name="is_active"
                  control={control}
                  render={({ field }) => (
                    <FormControlLabel
                      control={
                        <Switch
                          checked={field.value}
                          onChange={(e) => field.onChange(e.target.checked)}
                        />
                      }
                      label="Active"
                    />
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
              Edit the polygon to redefine the region boundary. Use the edit/delete tools on the right.
            </Typography>
            <BoundaryDrawer
              existingBoundary={boundary ?? undefined}
              onBoundaryChange={handleBoundaryChange}
              defaultCenter={{ lat: centerLat ?? -1, lng: centerLng ?? 37 }}
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
            <Button variant="outlined" onClick={() => navigate(`/regions/${regionId}`)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              startIcon={isSubmitting ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}
