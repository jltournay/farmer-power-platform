/**
 * Farmer Create Page
 *
 * Form for registering a new farmer with GPS location and collection point assignment.
 * Implements Story 9.5 - Farmer Management (AC 9.5.3).
 *
 * Features:
 * - Personal info form
 * - Farm info with GPS picker
 * - Collection point selection
 * - Communication preferences
 * - Validation and error handling (AC 9.5.7)
 */

import { useState, useEffect, useCallback } from 'react';
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
  Typography,
  Button,
  CircularProgress,
  InputAdornment,
  Snackbar,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import { PageHeader, GPSFieldWithMapAssist, type GPSCoordinates } from '@fp/ui-components';
import {
  createFarmer,
  listRegions,
  listFactories,
  listCollectionPoints,
  type RegionSummary,
  type FactorySummary,
  type CollectionPointSummary,
  NOTIFICATION_CHANNEL_OPTIONS,
  INTERACTION_PREF_OPTIONS,
  LANGUAGE_OPTIONS,
  farmerFormDataToCreateRequest,
} from '@/api';

// ============================================================================
// Validation Schema
// ============================================================================

const farmerFormSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  phone: z.string()
    .min(10, 'Phone must be at least 10 characters')
    .max(15, 'Phone must be at most 15 characters')
    .regex(/^\+/, 'Phone must start with + (E.164 format)'),
  national_id: z.string().min(1, 'National ID is required').max(20),
  collection_point_id: z.string().min(1, 'Collection point is required'),
  farm_size_hectares: z.coerce.number().min(0.01, 'Minimum 0.01 hectares').max(1000),
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
  grower_number: z.string().max(50).optional(),
  notification_channel: z.enum(['sms', 'whatsapp', 'push', 'voice']),
  interaction_pref: z.enum(['text', 'voice', 'visual']),
  pref_lang: z.enum(['sw', 'en', 'ki', 'luo']),
});

type FormValues = z.infer<typeof farmerFormSchema>;

const defaultValues: FormValues = {
  first_name: '',
  last_name: '',
  phone: '+254',
  national_id: '',
  collection_point_id: '',
  farm_size_hectares: 0.5,
  latitude: -1.0,
  longitude: 37.0,
  grower_number: '',
  notification_channel: 'sms',
  interaction_pref: 'text',
  pref_lang: 'sw',
};

// ============================================================================
// Component
// ============================================================================

export function FarmerCreate(): JSX.Element {
  const navigate = useNavigate();

  // State
  const [regions, setRegions] = useState<RegionSummary[]>([]);
  const [factories, setFactories] = useState<FactorySummary[]>([]);
  const [collectionPoints, setCollectionPoints] = useState<CollectionPointSummary[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [selectedFactory, setSelectedFactory] = useState<string>('');
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successSnackbar, setSuccessSnackbar] = useState(false);
  const [loadingLookups, setLoadingLookups] = useState(true);

  // Form state
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(farmerFormSchema),
    defaultValues,
  });

  // Watch location for map
  const latitude = watch('latitude');
  const longitude = watch('longitude');

  // Fetch regions
  const fetchRegions = useCallback(async () => {
    try {
      const response = await listRegions({ page_size: 100, active_only: true });
      setRegions(response.data);
    } catch {
      console.warn('Failed to load regions');
    }
  }, []);

  // Fetch factories when region changes
  const fetchFactories = useCallback(async (regionId: string) => {
    if (!regionId) {
      setFactories([]);
      return;
    }
    try {
      const response = await listFactories({ region_id: regionId, page_size: 100, active_only: true });
      setFactories(response.data);
    } catch {
      console.warn('Failed to load factories');
    }
  }, []);

  // Fetch collection points when factory changes
  const fetchCollectionPoints = useCallback(async (factoryId: string) => {
    if (!factoryId) {
      setCollectionPoints([]);
      return;
    }
    try {
      const response = await listCollectionPoints({ factory_id: factoryId, page_size: 100 });
      setCollectionPoints(response.data);
    } catch {
      console.warn('Failed to load collection points');
    }
  }, []);

  useEffect(() => {
    fetchRegions().finally(() => setLoadingLookups(false));
  }, [fetchRegions]);

  useEffect(() => {
    if (selectedRegion) {
      fetchFactories(selectedRegion);
      setSelectedFactory('');
      setCollectionPoints([]);
      setValue('collection_point_id', '');
    }
  }, [selectedRegion, fetchFactories, setValue]);

  useEffect(() => {
    if (selectedFactory) {
      fetchCollectionPoints(selectedFactory);
      setValue('collection_point_id', '');
    }
  }, [selectedFactory, fetchCollectionPoints, setValue]);

  // Handle GPS change from map
  const handleGPSChange = (coords: GPSCoordinates) => {
    if (coords.lat !== null) setValue('latitude', coords.lat);
    if (coords.lng !== null) setValue('longitude', coords.lng);
  };

  // Form submission
  const onSubmit = async (data: FormValues) => {
    setSubmitError(null);

    try {
      const request = farmerFormDataToCreateRequest({
        ...data,
        grower_number: data.grower_number ?? '',
      });
      const created = await createFarmer(request);
      setSuccessSnackbar(true);
      // Navigate after brief delay to show snackbar
      setTimeout(() => navigate(`/farmers/${created.id}`), 1000);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create farmer');
    }
  };

  if (loadingLookups) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <PageHeader
        title="Add New Farmer"
        subtitle="Register a new farmer with their farm details and collection point assignment"
        onBack={() => navigate('/farmers')}
        actions={[
          {
            id: 'save',
            label: isSubmitting ? 'Creating...' : 'Create Farmer',
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
        {/* Personal Information */}
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Personal Information
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="first_name"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="First Name"
                      fullWidth
                      required
                      error={!!errors.first_name}
                      helperText={errors.first_name?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="last_name"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Last Name"
                      fullWidth
                      required
                      error={!!errors.last_name}
                      helperText={errors.last_name?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="phone"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Phone Number"
                      fullWidth
                      required
                      placeholder="+254712345678"
                      error={!!errors.phone}
                      helperText={errors.phone?.message || 'E.164 format (e.g., +254712345678)'}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="national_id"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="National ID"
                      fullWidth
                      required
                      error={!!errors.national_id}
                      helperText={errors.national_id?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="grower_number"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Grower Number (Optional)"
                      fullWidth
                      error={!!errors.grower_number}
                      helperText={errors.grower_number?.message || 'External/legacy grower number'}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Collection Point Assignment */}
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Collection Point Assignment
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select a region, then factory, then collection point to assign this farmer.
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  select
                  label="Region"
                  fullWidth
                  value={selectedRegion}
                  onChange={(e) => setSelectedRegion(e.target.value)}
                  required
                >
                  <MenuItem value="">Select a region</MenuItem>
                  {regions.map((region) => (
                    <MenuItem key={region.id} value={region.id}>
                      {region.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  select
                  label="Factory"
                  fullWidth
                  value={selectedFactory}
                  onChange={(e) => setSelectedFactory(e.target.value)}
                  disabled={!selectedRegion}
                  required
                >
                  <MenuItem value="">Select a factory</MenuItem>
                  {factories.map((factory) => (
                    <MenuItem key={factory.id} value={factory.id}>
                      {factory.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <Controller
                  name="collection_point_id"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Collection Point"
                      fullWidth
                      disabled={!selectedFactory}
                      required
                      error={!!errors.collection_point_id}
                      helperText={errors.collection_point_id?.message}
                    >
                      <MenuItem value="">Select a collection point</MenuItem>
                      {collectionPoints.map((cp) => (
                        <MenuItem key={cp.id} value={cp.id}>
                          {cp.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Farm Information */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Farm Location
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Click on the map or enter coordinates to set the farm location.
            </Typography>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="farm_size_hectares"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Farm Size"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.farm_size_hectares}
                      helperText={errors.farm_size_hectares?.message}
                      InputProps={{
                        endAdornment: <InputAdornment position="end">hectares</InputAdornment>,
                      }}
                      inputProps={{ step: 0.01, min: 0.01 }}
                    />
                  )}
                />
              </Grid>
            </Grid>
            <GPSFieldWithMapAssist
              value={{ lat: latitude ?? 0, lng: longitude ?? 0 }}
              onChange={handleGPSChange}
            />
          </Paper>
        </Grid>

        {/* Communication Preferences */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Communication Preferences
            </Typography>
            <Grid container spacing={2}>
              <Grid size={12}>
                <Controller
                  name="notification_channel"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Notification Channel"
                      fullWidth
                      error={!!errors.notification_channel}
                      helperText={errors.notification_channel?.message}
                    >
                      {NOTIFICATION_CHANNEL_OPTIONS.map((opt) => (
                        <MenuItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Grid>
              <Grid size={12}>
                <Controller
                  name="interaction_pref"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Information Preference"
                      fullWidth
                      error={!!errors.interaction_pref}
                      helperText={errors.interaction_pref?.message || 'How they prefer to receive information'}
                    >
                      {INTERACTION_PREF_OPTIONS.map((opt) => (
                        <MenuItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Grid>
              <Grid size={12}>
                <Controller
                  name="pref_lang"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Preferred Language"
                      fullWidth
                      error={!!errors.pref_lang}
                      helperText={errors.pref_lang?.message}
                    >
                      {LANGUAGE_OPTIONS.map((opt) => (
                        <MenuItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Submit Button (mobile) */}
        <Grid size={12}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            <Button variant="outlined" onClick={() => navigate('/farmers')}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              startIcon={isSubmitting ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Creating...' : 'Create Farmer'}
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Success Snackbar */}
      <Snackbar
        open={successSnackbar}
        autoHideDuration={3000}
        onClose={() => setSuccessSnackbar(false)}
        message="Farmer created successfully"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
}
