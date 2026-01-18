/**
 * Farmer Create Page
 *
 * Form for registering a new farmer with GPS location.
 * Implements Story 9.5 - Farmer Management (AC 9.5.3).
 *
 * Story 9.5a: Collection point assignment removed - CP is assigned on first delivery
 * or via separate assignment API.
 *
 * Features:
 * - Personal info form
 * - Farm info with GPS picker
 * - Communication preferences
 * - Validation and error handling (AC 9.5.7)
 */

import { useState, useCallback } from 'react';
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
  // Story 9.5a: Removed listRegions, listFactories, listCollectionPoints - CP assignment removed
  NOTIFICATION_CHANNEL_OPTIONS,
  INTERACTION_PREF_OPTIONS,
  LANGUAGE_OPTIONS,
  farmerFormDataToCreateRequest,
} from '@/api';

// ============================================================================
// Validation Schema
// ============================================================================

// Story 9.5a: collection_point_id removed - CP is assigned on first delivery
const farmerFormSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  phone: z.string()
    .min(10, 'Phone must be at least 10 characters')
    .max(15, 'Phone must be at most 15 characters')
    .regex(/^\+/, 'Phone must start with + (E.164 format)'),
  national_id: z.string().min(1, 'National ID is required').max(20),
  // Story 9.5a: collection_point_id removed
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
  // Story 9.5a: collection_point_id removed
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

  // State - Story 9.5a: Removed region/factory/collectionPoints state - CP assignment removed
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successSnackbar, setSuccessSnackbar] = useState(false);

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

  // Story 9.5a: Removed fetchRegions, fetchFactories, fetchCollectionPoints
  // CP assignment is now done on first delivery or via separate API

  // Handle GPS change from map
  const handleGPSChange = useCallback((coords: GPSCoordinates) => {
    if (coords.lat !== null) setValue('latitude', coords.lat);
    if (coords.lng !== null) setValue('longitude', coords.lng);
  }, [setValue]);

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

  // Story 9.5a: Removed loadingLookups - no longer fetching lookups for CP assignment

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <PageHeader
        title="Add New Farmer"
        subtitle="Register a new farmer with their farm details (CP assigned on first delivery)"
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

        {/* Story 9.5a: Collection Point Assignment section removed - CP assigned on first delivery */}

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
