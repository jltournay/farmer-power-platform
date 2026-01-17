/**
 * Collection Point Edit Page
 *
 * Form for editing collection point configuration.
 * Implements Story 9.4 - Collection Point Management (AC3, AC4, AC6, AC7).
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import {
  Box,
  Alert,
  CircularProgress,
  Paper,
  Grid2 as Grid,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  FormGroup,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import { PageHeader } from '@fp/ui-components';
import {
  getCollectionPoint,
  getFactory,
  updateCollectionPoint,
  type CollectionPointDetailFull,
  type CollectionPointFormData,
  type FactoryDetail,
  cpDetailToFormData,
  cpFormDataToUpdateRequest,
  CP_FORM_DEFAULTS,
  COLLECTION_DAYS,
  STORAGE_TYPE_OPTIONS,
} from '@/api';

/**
 * Collection point edit form validation rules.
 */
const VALIDATION_RULES = {
  name: {
    required: 'Name is required',
    minLength: { value: 2, message: 'Name must be at least 2 characters' },
    maxLength: { value: 100, message: 'Name must be at most 100 characters' },
  },
  weekday_hours: {
    required: 'Weekday hours are required',
    pattern: {
      value: /^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$/,
      message: 'Format: HH:MM-HH:MM (e.g., 06:00-10:00)',
    },
  },
  weekend_hours: {
    required: 'Weekend hours are required',
    pattern: {
      value: /^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$/,
      message: 'Format: HH:MM-HH:MM (e.g., 07:00-09:00)',
    },
  },
  max_daily_kg: {
    required: 'Max daily capacity is required',
    min: { value: 0, message: 'Cannot be negative' },
    max: { value: 100000, message: 'Cannot exceed 100,000 kg' },
  },
  clerk_phone: {
    pattern: {
      value: /^(\+?[0-9]{10,15})?$/,
      message: 'Invalid phone number format',
    },
  },
};

/**
 * Collection day labels for display.
 */
const DAY_LABELS: Record<string, string> = {
  mon: 'Monday',
  tue: 'Tuesday',
  wed: 'Wednesday',
  thu: 'Thursday',
  fri: 'Friday',
  sat: 'Saturday',
  sun: 'Sunday',
};

/**
 * Collection point edit page component.
 */
export function CollectionPointEdit(): JSX.Element {
  const { factoryId, cpId } = useParams<{ factoryId: string; cpId: string }>();
  const navigate = useNavigate();

  // State
  const [cp, setCp] = useState<CollectionPointDetailFull | null>(null);
  const [factory, setFactory] = useState<FactoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const [statusChangeDialog, setStatusChangeDialog] = useState<{
    open: boolean;
    newStatus: string;
  }>({ open: false, newStatus: '' });

  // Form setup
  const {
    control,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isDirty },
  } = useForm<CollectionPointFormData>({
    defaultValues: CP_FORM_DEFAULTS,
  });

  // Unused: currentStatus = watch('status') - status changes handled in handleStatusChange

  // Fetch data
  const fetchData = useCallback(async () => {
    if (!cpId || !factoryId) return;

    setLoading(true);
    setError(null);

    try {
      const [cpData, factoryData] = await Promise.all([
        getCollectionPoint(cpId),
        getFactory(factoryId),
      ]);
      setCp(cpData);
      setFactory(factoryData);

      // Populate form with existing data
      const formData = cpDetailToFormData(cpData);
      reset(formData);
    } catch (err) {
      if (err instanceof Error) {
        if (err.message.includes('404') || err.message.includes('not found')) {
          setError('Collection Point not found');
        } else {
          setError(err.message);
        }
      } else {
        setError('Failed to load collection point');
      }
    } finally {
      setLoading(false);
    }
  }, [cpId, factoryId, reset]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle form submission
  const onSubmit = async (data: CollectionPointFormData) => {
    if (!cpId) return;

    setSaving(true);
    try {
      const request = cpFormDataToUpdateRequest(data);
      await updateCollectionPoint(cpId, request);

      setSnackbar({
        open: true,
        message: 'Collection point updated successfully',
        severity: 'success',
      });

      // Navigate back to detail page after short delay
      setTimeout(() => {
        navigate(`/factories/${factoryId}/collection-points/${cpId}`);
      }, 1000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update collection point';
      setSnackbar({
        open: true,
        message,
        severity: 'error',
      });
    } finally {
      setSaving(false);
    }
  };

  // Handle status change with confirmation
  const handleStatusChange = (newStatus: string) => {
    if (cp && newStatus !== cp.status) {
      setStatusChangeDialog({ open: true, newStatus });
    }
  };

  const confirmStatusChange = () => {
    setValue('status', statusChangeDialog.newStatus as 'active' | 'inactive' | 'seasonal', {
      shouldDirty: true,
    });
    setStatusChangeDialog({ open: false, newStatus: '' });
  };

  const cancelStatusChange = () => {
    // Reset to original status
    if (cp) {
      setValue('status', cp.status, { shouldDirty: false });
    }
    setStatusChangeDialog({ open: false, newStatus: '' });
  };

  // Handle cancel
  const handleCancel = () => {
    if (isDirty) {
      const confirmed = window.confirm('You have unsaved changes. Are you sure you want to leave?');
      if (!confirmed) return;
    }
    navigate(`/factories/${factoryId}/collection-points/${cpId}`);
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
          title="Edit Collection Point"
          onBack={() => navigate(`/factories/${factoryId}`)}
        />
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!cp || !factory) {
    return (
      <Box>
        <PageHeader
          title="Edit Collection Point"
          onBack={() => navigate(`/factories/${factoryId}`)}
        />
        <Alert severity="warning">Collection point data not available</Alert>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      {/* Page Header */}
      <PageHeader
        title={`Edit: ${cp.name}`}
        subtitle={`Factory: ${factory.name} | ID: ${cp.id}`}
        onBack={handleCancel}
        actions={[
          {
            id: 'cancel',
            label: 'Cancel',
            icon: <CancelIcon />,
            variant: 'outlined',
            onClick: handleCancel,
          },
          {
            id: 'save',
            label: saving ? 'Saving...' : 'Save Changes',
            icon: <SaveIcon />,
            variant: 'contained',
            onClick: () => handleSubmit(onSubmit)(),
            disabled: saving || !isDirty,
          },
        ]}
      />

      <Grid container spacing={3}>
        {/* Basic Information */}
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Basic Information
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Controller
                  name="name"
                  control={control}
                  rules={VALIDATION_RULES.name}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Collection Point Name"
                      fullWidth
                      error={!!errors.name}
                      helperText={errors.name?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Controller
                  name="status"
                  control={control}
                  render={({ field }) => (
                    <FormControl fullWidth>
                      <InputLabel>Status</InputLabel>
                      <Select
                        {...field}
                        label="Status"
                        onChange={(e) => {
                          handleStatusChange(e.target.value);
                        }}
                      >
                        <MenuItem value="active">Active</MenuItem>
                        <MenuItem value="inactive">Inactive</MenuItem>
                        <MenuItem value="seasonal">Seasonal</MenuItem>
                      </Select>
                    </FormControl>
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Clerk Assignment */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Clerk Assignment
            </Typography>
            <Grid container spacing={2}>
              <Grid size={12}>
                <Controller
                  name="clerk_id"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Clerk ID"
                      fullWidth
                      placeholder="Leave empty if no clerk"
                    />
                  )}
                />
              </Grid>
              <Grid size={12}>
                <Controller
                  name="clerk_phone"
                  control={control}
                  rules={VALIDATION_RULES.clerk_phone}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Clerk Phone"
                      fullWidth
                      placeholder="+254..."
                      error={!!errors.clerk_phone}
                      helperText={errors.clerk_phone?.message}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Operating Hours */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Operating Hours
            </Typography>
            <Grid container spacing={2}>
              <Grid size={12}>
                <Controller
                  name="weekday_hours"
                  control={control}
                  rules={VALIDATION_RULES.weekday_hours}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Weekday Hours"
                      fullWidth
                      placeholder="06:00-10:00"
                      error={!!errors.weekday_hours}
                      helperText={errors.weekday_hours?.message || 'Format: HH:MM-HH:MM (24-hour)'}
                    />
                  )}
                />
              </Grid>
              <Grid size={12}>
                <Controller
                  name="weekend_hours"
                  control={control}
                  rules={VALIDATION_RULES.weekend_hours}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Weekend Hours"
                      fullWidth
                      placeholder="07:00-09:00"
                      error={!!errors.weekend_hours}
                      helperText={errors.weekend_hours?.message || 'Format: HH:MM-HH:MM (24-hour)'}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Collection Days */}
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Collection Days
            </Typography>
            <Controller
              name="collection_days"
              control={control}
              render={({ field }) => (
                <FormGroup row>
                  {COLLECTION_DAYS.map((day) => (
                    <FormControlLabel
                      key={day}
                      control={
                        <Checkbox
                          checked={field.value?.includes(day) ?? false}
                          onChange={(e) => {
                            const newValue = e.target.checked
                              ? [...(field.value ?? []), day]
                              : (field.value ?? []).filter((d) => d !== day);
                            field.onChange(newValue);
                          }}
                        />
                      }
                      label={DAY_LABELS[day]}
                    />
                  ))}
                </FormGroup>
              )}
            />
          </Paper>
        </Grid>

        {/* Capacity & Equipment */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Capacity
            </Typography>
            <Grid container spacing={2}>
              <Grid size={12}>
                <Controller
                  name="max_daily_kg"
                  control={control}
                  rules={VALIDATION_RULES.max_daily_kg}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Max Daily Capacity (kg)"
                      type="number"
                      fullWidth
                      error={!!errors.max_daily_kg}
                      helperText={errors.max_daily_kg?.message}
                      inputProps={{ min: 0, max: 100000 }}
                      onChange={(e) => field.onChange(parseInt(e.target.value, 10) || 0)}
                    />
                  )}
                />
              </Grid>
              <Grid size={12}>
                <Controller
                  name="storage_type"
                  control={control}
                  render={({ field }) => (
                    <FormControl fullWidth>
                      <InputLabel>Storage Type</InputLabel>
                      <Select {...field} label="Storage Type">
                        {STORAGE_TYPE_OPTIONS.map((opt) => (
                          <MenuItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Equipment */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Equipment
            </Typography>
            <FormGroup>
              <Controller
                name="has_weighing_scale"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={field.value}
                        onChange={(e) => field.onChange(e.target.checked)}
                      />
                    }
                    label="Has Weighing Scale"
                  />
                )}
              />
              <Controller
                name="has_qc_device"
                control={control}
                render={({ field }) => (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={field.value}
                        onChange={(e) => field.onChange(e.target.checked)}
                      />
                    }
                    label="Has QC Device"
                  />
                )}
              />
            </FormGroup>
          </Paper>
        </Grid>

        {/* Read-only info */}
        <Grid size={12}>
          <Paper sx={{ p: 3, bgcolor: 'grey.50' }}>
            <Typography variant="h6" gutterBottom color="text.secondary">
              Read-Only Information
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">Collection Point ID</Typography>
                <Typography variant="body1">{cp.id}</Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">Factory</Typography>
                <Typography variant="body1">{factory.name}</Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">Region</Typography>
                <Typography variant="body1">{cp.region_id}</Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">Farmers</Typography>
                <Typography variant="body1">{cp.farmer_count}</Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">Location</Typography>
                <Typography variant="body1">
                  {cp.location.latitude.toFixed(4)}, {cp.location.longitude.toFixed(4)}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">Created</Typography>
                <Typography variant="body1">
                  {new Date(cp.created_at).toLocaleDateString()}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">Last Updated</Typography>
                <Typography variant="body1">
                  {new Date(cp.updated_at).toLocaleDateString()}
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>

      {/* Status Change Confirmation Dialog */}
      <Dialog open={statusChangeDialog.open} onClose={cancelStatusChange}>
        <DialogTitle>Confirm Status Change</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to change the status from{' '}
            <strong>{cp.status}</strong> to{' '}
            <strong>{statusChangeDialog.newStatus}</strong>?
            {statusChangeDialog.newStatus === 'inactive' && (
              <>
                <br /><br />
                <Alert severity="warning" sx={{ mt: 1 }}>
                  Setting status to inactive will prevent farmers from delivering to this collection point.
                </Alert>
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelStatusChange}>Cancel</Button>
          <Button onClick={confirmStatusChange} variant="contained" color="primary">
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success/Error Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
