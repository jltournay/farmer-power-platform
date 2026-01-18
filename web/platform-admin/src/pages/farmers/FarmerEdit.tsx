/**
 * Farmer Edit Page
 *
 * Form for editing an existing farmer with editable/read-only field separation.
 * Implements Story 9.5 - Farmer Management (AC 9.5.4).
 *
 * Story 9.5a: collection_point_id replaced with collection_points array (N:M model).
 *
 * Features:
 * - Editable fields: name, phone, farm size, communication preferences
 * - Read-only fields: national_id, region_id, farm_location
 * - Collection points shown as read-only (assigned via delivery)
 * - Deactivation toggle (AC 9.5.6)
 * - Validation and error handling (AC 9.5.7)
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
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
  FormControlLabel,
  Switch,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Snackbar,
  Divider,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import LockIcon from '@mui/icons-material/Lock';
import { PageHeader, GPSFieldWithMapAssist } from '@fp/ui-components';
import {
  getFarmer,
  updateFarmer,
  listRegions,
  type FarmerDetail,
  type FarmerUpdateRequest,
  type RegionSummary,
  NOTIFICATION_CHANNEL_OPTIONS,
  INTERACTION_PREF_OPTIONS,
  LANGUAGE_OPTIONS,
  FARM_SCALE_OPTIONS,
} from '@/api';

// ============================================================================
// Validation Schema (only editable fields)
// ============================================================================

const farmerEditSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  phone: z.string()
    .min(10, 'Phone must be at least 10 characters')
    .max(15, 'Phone must be at most 15 characters')
    .regex(/^\+/, 'Phone must start with + (E.164 format)'),
  farm_size_hectares: z.coerce.number().min(0.01, 'Minimum 0.01 hectares').max(1000),
  notification_channel: z.enum(['sms', 'whatsapp', 'push', 'voice']),
  interaction_pref: z.enum(['text', 'voice', 'visual']),
  pref_lang: z.enum(['sw', 'en', 'ki', 'luo']),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof farmerEditSchema>;

// ============================================================================
// Component
// ============================================================================

export function FarmerEdit(): JSX.Element {
  const { farmerId } = useParams<{ farmerId: string }>();
  const navigate = useNavigate();

  // State
  const [farmer, setFarmer] = useState<FarmerDetail | null>(null);
  const [regions, setRegions] = useState<RegionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);
  const [successSnackbar, setSuccessSnackbar] = useState(false);

  // Form state
  const {
    control,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(farmerEditSchema),
  });

  // Region lookup map
  const regionMap = regions.reduce<Record<string, string>>((acc, r) => {
    acc[r.id] = r.name;
    return acc;
  }, {});

  // Fetch farmer data
  const fetchFarmer = useCallback(async () => {
    if (!farmerId) return;

    setLoading(true);
    setLoadError(null);

    try {
      const data = await getFarmer(farmerId);
      setFarmer(data);

      // Reset form with farmer data
      reset({
        first_name: data.first_name,
        last_name: data.last_name,
        phone: data.phone,
        farm_size_hectares: data.farm_size_hectares,
        notification_channel: data.communication_prefs.notification_channel,
        interaction_pref: data.communication_prefs.interaction_pref,
        pref_lang: data.communication_prefs.pref_lang,
        is_active: data.is_active,
      });
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load farmer');
    } finally {
      setLoading(false);
    }
  }, [farmerId, reset]);

  // Fetch regions for display
  const fetchRegions = useCallback(async () => {
    try {
      const response = await listRegions({ page_size: 100 });
      setRegions(response.data);
    } catch {
      console.warn('Failed to load regions');
    }
  }, []);

  useEffect(() => {
    fetchFarmer();
    fetchRegions();
  }, [fetchFarmer, fetchRegions]);

  // Handle deactivation toggle - show confirmation dialog
  const handleActiveToggle = (newValue: boolean) => {
    if (!newValue && farmer?.is_active) {
      // Deactivating - show confirmation dialog
      setDeactivateDialogOpen(true);
    } else {
      // Activating - no confirmation needed
      setValue('is_active', newValue, { shouldDirty: true });
    }
  };

  // Confirm deactivation
  const handleConfirmDeactivate = () => {
    setValue('is_active', false, { shouldDirty: true });
    setDeactivateDialogOpen(false);
  };

  // Cancel deactivation
  const handleCancelDeactivate = () => {
    setDeactivateDialogOpen(false);
  };

  // Form submission
  const onSubmit = async (data: FormValues) => {
    if (!farmerId) return;
    setSubmitError(null);

    try {
      const request: FarmerUpdateRequest = {
        first_name: data.first_name,
        last_name: data.last_name,
        phone: data.phone,
        farm_size_hectares: data.farm_size_hectares,
        notification_channel: data.notification_channel,
        interaction_pref: data.interaction_pref,
        pref_lang: data.pref_lang,
        is_active: data.is_active,
      };

      await updateFarmer(farmerId, request);
      setSuccessSnackbar(true);
      // Navigate after brief delay to show snackbar
      setTimeout(() => navigate(`/farmers/${farmerId}`), 1000);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to update farmer');
    }
  };

  // Helper functions for display
  const getFarmScaleLabel = (scale: string): string => {
    const option = FARM_SCALE_OPTIONS.find((o) => o.value === scale);
    return option?.label ?? scale;
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
        <PageHeader title="Edit Farmer" onBack={() => navigate('/farmers')} />
        <Alert severity="error">{loadError}</Alert>
      </Box>
    );
  }

  if (!farmer) {
    return (
      <Box>
        <PageHeader title="Edit Farmer" onBack={() => navigate('/farmers')} />
        <Alert severity="warning">Farmer not found</Alert>
      </Box>
    );
  }

  const fullName = `${farmer.first_name} ${farmer.last_name}`;

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <PageHeader
        title={`Edit: ${fullName}`}
        subtitle={`ID: ${farmer.id}${farmer.grower_number ? ` | Grower #: ${farmer.grower_number}` : ''}`}
        onBack={() => navigate(`/farmers/${farmerId}`)}
        statusBadge={
          <Chip
            label={farmer.is_active ? 'Active' : 'Inactive'}
            color={farmer.is_active ? 'success' : 'default'}
            size="small"
          />
        }
        actions={[
          {
            id: 'save',
            label: isSubmitting ? 'Saving...' : 'Save Changes',
            icon: isSubmitting ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />,
            variant: 'contained',
            onClick: handleSubmit(onSubmit),
            disabled: isSubmitting || !isDirty,
          },
        ]}
      />

      {submitError && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setSubmitError(null)}>
          {submitError}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Personal Information (Editable) */}
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
                <TextField
                  label="National ID"
                  fullWidth
                  value={farmer.national_id}
                  disabled
                  InputProps={{
                    startAdornment: <LockIcon fontSize="small" color="disabled" sx={{ mr: 1 }} />,
                  }}
                  helperText="Cannot be changed after registration"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Grower Number"
                  fullWidth
                  value={farmer.grower_number ?? '—'}
                  disabled
                  InputProps={{
                    startAdornment: <LockIcon fontSize="small" color="disabled" sx={{ mr: 1 }} />,
                  }}
                  helperText="Cannot be changed after registration"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="is_active"
                  control={control}
                  render={({ field }) => (
                    <FormControlLabel
                      control={
                        <Switch
                          checked={field.value}
                          onChange={(e) => handleActiveToggle(e.target.checked)}
                        />
                      }
                      label="Farmer Active"
                    />
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
              Farm Information
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="farm_size_hectares"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Farm Size (hectares)"
                      type="number"
                      fullWidth
                      required
                      error={!!errors.farm_size_hectares}
                      helperText={errors.farm_size_hectares?.message}
                      inputProps={{ step: 0.01, min: 0.01 }}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Farm Scale"
                  fullWidth
                  value={getFarmScaleLabel(farmer.farm_scale)}
                  disabled
                  helperText="Auto-calculated from farm size"
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Read-only location and assignment info */}
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
              <LockIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
              Read-only Information (contact administrator to change)
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Region"
                  fullWidth
                  value={regionMap[farmer.region_id] ?? farmer.region_id}
                  disabled
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                {/* Story 9.5a: collection_point_id → collection_points (N:M model) */}
                <TextField
                  label="Collection Points"
                  fullWidth
                  value={
                    farmer.collection_points.length > 0
                      ? farmer.collection_points.map((cp) => cp.name).join(', ')
                      : 'None assigned (assigned on delivery)'
                  }
                  disabled
                  helperText="Assigned automatically on delivery"
                />
              </Grid>
            </Grid>

            <Typography variant="subtitle2" sx={{ mt: 3, mb: 1 }}>
              Farm Location
            </Typography>
            <GPSFieldWithMapAssist
              value={{
                lat: farmer.farm_location.latitude,
                lng: farmer.farm_location.longitude,
              }}
              onChange={() => {}} // Read-only
              disabled={true}
            />
            {farmer.farm_location.altitude_meters !== undefined && farmer.farm_location.altitude_meters !== 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Altitude: {farmer.farm_location.altitude_meters.toFixed(0)}m
              </Typography>
            )}
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
            <Button variant="outlined" onClick={() => navigate(`/farmers/${farmerId}`)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              startIcon={isSubmitting ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
              disabled={isSubmitting || !isDirty}
            >
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Deactivation Confirmation Dialog (AC 9.5.6) */}
      <Dialog open={deactivateDialogOpen} onClose={handleCancelDeactivate}>
        <DialogTitle>Deactivate Farmer?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to deactivate <strong>{fullName}</strong>?
            <br />
            <br />
            Deactivated farmers will no longer be able to make deliveries and will be excluded from
            active farmer lists. This action can be reversed later.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelDeactivate}>Cancel</Button>
          <Button onClick={handleConfirmDeactivate} color="warning" variant="contained">
            Deactivate
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={successSnackbar}
        autoHideDuration={3000}
        onClose={() => setSuccessSnackbar(false)}
        message="Farmer updated successfully"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
}
