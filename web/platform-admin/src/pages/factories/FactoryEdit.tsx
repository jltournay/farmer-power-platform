/**
 * Factory Edit Page
 *
 * Form for editing an existing factory with location, thresholds, and payment policy.
 * Implements Story 9.3 - Factory Management (AC4).
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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  InputAdornment,
  FormControlLabel,
  Switch,
  Chip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SaveIcon from '@mui/icons-material/Save';
import { PageHeader, GPSFieldWithMapAssist, type GPSCoordinates } from '@fp/ui-components';
import {
  getFactory,
  updateFactory,
  listRegions,
  type FactoryUpdateRequest,
  type FactoryDetail,
  type RegionSummary,
  type PaymentPolicyType,
} from '@/api';

// ============================================================================
// Validation Schema
// ============================================================================

const factoryFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  code: z.string().min(1, 'Code is required').max(20),
  region_id: z.string().min(1, 'Region is required'),
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
  phone: z.string().max(20).optional(),
  email: z.string().email('Invalid email').max(100).optional().or(z.literal('')),
  address: z.string().max(200).optional(),
  processing_capacity_kg: z.coerce.number().min(0),
  // Quality thresholds
  tier_1: z.coerce.number().min(0).max(100),
  tier_2: z.coerce.number().min(0).max(100),
  tier_3: z.coerce.number().min(0).max(100),
  // Payment policy
  policy_type: z.enum(['feedback_only', 'split_payment', 'weekly_bonus', 'delayed_payment']),
  tier_1_adjustment: z.coerce.number().min(-1).max(1),
  tier_2_adjustment: z.coerce.number().min(-1).max(1),
  tier_3_adjustment: z.coerce.number().min(-1).max(1),
  below_tier_3_adjustment: z.coerce.number().min(-1).max(1),
  // Status
  is_active: z.boolean(),
}).refine((data) => data.tier_1 > data.tier_2, {
  message: 'Tier 1 must be greater than Tier 2',
  path: ['tier_2'],
}).refine((data) => data.tier_2 > data.tier_3, {
  message: 'Tier 2 must be greater than Tier 3',
  path: ['tier_3'],
});

type FormValues = z.infer<typeof factoryFormSchema>;

// ============================================================================
// Component
// ============================================================================

export function FactoryEdit(): JSX.Element {
  const { factoryId } = useParams<{ factoryId: string }>();
  const navigate = useNavigate();

  // State
  const [factory, setFactory] = useState<FactoryDetail | null>(null);
  const [regions, setRegions] = useState<RegionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Form state
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(factoryFormSchema),
  });

  // Watch location for map
  const latitude = watch('latitude');
  const longitude = watch('longitude');

  // Region lookup map
  const regionMap = regions.reduce<Record<string, string>>((acc, r) => {
    acc[r.id] = r.name;
    return acc;
  }, {});

  // Fetch factory data
  const fetchFactory = useCallback(async () => {
    if (!factoryId) return;

    setLoading(true);
    setLoadError(null);

    try {
      const data = await getFactory(factoryId);
      setFactory(data);

      // Reset form with factory data
      reset({
        name: data.name,
        code: data.code,
        region_id: data.region_id,
        latitude: data.location.latitude,
        longitude: data.location.longitude,
        phone: data.contact.phone ?? '',
        email: data.contact.email ?? '',
        address: data.contact.address ?? '',
        processing_capacity_kg: data.processing_capacity_kg,
        tier_1: data.quality_thresholds.tier_1,
        tier_2: data.quality_thresholds.tier_2,
        tier_3: data.quality_thresholds.tier_3,
        policy_type: data.payment_policy.policy_type,
        tier_1_adjustment: data.payment_policy.tier_1_adjustment,
        tier_2_adjustment: data.payment_policy.tier_2_adjustment,
        tier_3_adjustment: data.payment_policy.tier_3_adjustment,
        below_tier_3_adjustment: data.payment_policy.below_tier_3_adjustment,
        is_active: data.is_active,
      });
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load factory');
    } finally {
      setLoading(false);
    }
  }, [factoryId, reset]);

  // Fetch regions for dropdown
  const fetchRegions = useCallback(async () => {
    try {
      const response = await listRegions({ page_size: 100 });
      setRegions(response.data);
    } catch {
      console.warn('Failed to load regions');
    }
  }, []);

  useEffect(() => {
    fetchFactory();
    fetchRegions();
  }, [fetchFactory, fetchRegions]);

  // Handle GPS change from map
  const handleGPSChange = (coords: GPSCoordinates) => {
    if (coords.lat !== null) setValue('latitude', coords.lat, { shouldDirty: true });
    if (coords.lng !== null) setValue('longitude', coords.lng, { shouldDirty: true });
  };

  // Form submission
  const onSubmit = async (data: FormValues) => {
    if (!factoryId) return;
    setSubmitError(null);

    try {
      const request: FactoryUpdateRequest = {
        name: data.name,
        code: data.code,
        location: {
          latitude: data.latitude,
          longitude: data.longitude,
        },
        contact: {
          phone: data.phone ?? '',
          email: data.email ?? '',
          address: data.address ?? '',
        },
        processing_capacity_kg: data.processing_capacity_kg,
        quality_thresholds: {
          tier_1: data.tier_1,
          tier_2: data.tier_2,
          tier_3: data.tier_3,
        },
        payment_policy: {
          policy_type: data.policy_type as PaymentPolicyType,
          tier_1_adjustment: data.tier_1_adjustment,
          tier_2_adjustment: data.tier_2_adjustment,
          tier_3_adjustment: data.tier_3_adjustment,
          below_tier_3_adjustment: data.below_tier_3_adjustment,
        },
        is_active: data.is_active,
      };

      await updateFactory(factoryId, request);
      navigate(`/factories/${factoryId}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to update factory');
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
          title="Edit Factory"
          onBack={() => navigate('/factories')}
        />
        <Alert severity="error">{loadError}</Alert>
      </Box>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <PageHeader
        title={`Edit: ${factory?.name ?? 'Factory'}`}
        subtitle={`Code: ${factory?.code ?? ''} | Region: ${regionMap[factory?.region_id ?? ''] ?? factory?.region_id ?? ''}`}
        onBack={() => navigate(`/factories/${factoryId}`)}
        statusBadge={
          factory ? (
            <Chip
              label={factory.is_active ? 'Active' : 'Inactive'}
              color={factory.is_active ? 'success' : 'default'}
              size="small"
            />
          ) : undefined
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
                      label="Factory Name"
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
                  name="code"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Factory Code"
                      fullWidth
                      required
                      error={!!errors.code}
                      helperText={errors.code?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="region_id"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Region"
                      fullWidth
                      required
                      disabled // Cannot change region after creation
                      error={!!errors.region_id}
                      helperText={errors.region_id?.message || 'Cannot change region after creation'}
                    >
                      {regions.map((region) => (
                        <MenuItem key={region.id} value={region.id}>
                          {region.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Controller
                  name="processing_capacity_kg"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Processing Capacity"
                      type="number"
                      fullWidth
                      error={!!errors.processing_capacity_kg}
                      helperText={errors.processing_capacity_kg?.message}
                      InputProps={{
                        endAdornment: <InputAdornment position="end">kg/day</InputAdornment>,
                      }}
                    />
                  )}
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
                          onChange={(e) => field.onChange(e.target.checked)}
                        />
                      }
                      label="Factory Active"
                    />
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Location */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Factory Location
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Click on the map or enter coordinates to update the factory location.
            </Typography>
            <GPSFieldWithMapAssist
              value={{ lat: latitude ?? 0, lng: longitude ?? 0 }}
              onChange={handleGPSChange}
            />
            {factory?.location.altitude_meters !== undefined && factory.location.altitude_meters !== 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Current altitude: {factory.location.altitude_meters.toFixed(0)}m (auto-updated on save)
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* Contact Information */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Contact Information
            </Typography>
            <Grid container spacing={2}>
              <Grid size={12}>
                <Controller
                  name="phone"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Phone"
                      fullWidth
                      error={!!errors.phone}
                      helperText={errors.phone?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={12}>
                <Controller
                  name="email"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Email"
                      fullWidth
                      error={!!errors.email}
                      helperText={errors.email?.message}
                    />
                  )}
                />
              </Grid>
              <Grid size={12}>
                <Controller
                  name="address"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Address"
                      fullWidth
                      multiline
                      rows={3}
                      error={!!errors.address}
                      helperText={errors.address?.message}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Quality Thresholds */}
        <Grid size={12}>
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Quality Thresholds</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Define minimum Primary % required for each quality tier.
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Controller
                    name="tier_1"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Premium Tier (Tier 1)"
                        type="number"
                        fullWidth
                        required
                        error={!!errors.tier_1}
                        helperText={errors.tier_1?.message}
                        InputProps={{
                          endAdornment: <InputAdornment position="end">%</InputAdornment>,
                        }}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Controller
                    name="tier_2"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Standard Tier (Tier 2)"
                        type="number"
                        fullWidth
                        required
                        error={!!errors.tier_2}
                        helperText={errors.tier_2?.message}
                        InputProps={{
                          endAdornment: <InputAdornment position="end">%</InputAdornment>,
                        }}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Controller
                    name="tier_3"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Acceptable Tier (Tier 3)"
                        type="number"
                        fullWidth
                        required
                        error={!!errors.tier_3}
                        helperText={errors.tier_3?.message}
                        InputProps={{
                          endAdornment: <InputAdornment position="end">%</InputAdornment>,
                        }}
                      />
                    )}
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>

        {/* Payment Policy */}
        <Grid size={12}>
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Payment Policy</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure quality-based payment adjustments.
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                  <Controller
                    name="policy_type"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        select
                        label="Policy Type"
                        fullWidth
                        required
                        error={!!errors.policy_type}
                        helperText={errors.policy_type?.message}
                      >
                        <MenuItem value="feedback_only">Feedback Only (No adjustment)</MenuItem>
                        <MenuItem value="split_payment">Split Payment</MenuItem>
                        <MenuItem value="weekly_bonus">Weekly Bonus</MenuItem>
                        <MenuItem value="delayed_payment">Delayed Payment</MenuItem>
                      </TextField>
                    )}
                  />
                </Grid>
              </Grid>
              <Typography variant="subtitle2" sx={{ mt: 3, mb: 1 }}>
                Rate Adjustments by Tier
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enter as decimal: 0.15 = +15%, -0.10 = -10%
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Controller
                    name="tier_1_adjustment"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Premium"
                        type="number"
                        fullWidth
                        error={!!errors.tier_1_adjustment}
                        helperText={errors.tier_1_adjustment?.message}
                        inputProps={{ step: 0.01, min: -1, max: 1 }}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Controller
                    name="tier_2_adjustment"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Standard"
                        type="number"
                        fullWidth
                        error={!!errors.tier_2_adjustment}
                        helperText={errors.tier_2_adjustment?.message}
                        inputProps={{ step: 0.01, min: -1, max: 1 }}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Controller
                    name="tier_3_adjustment"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Acceptable"
                        type="number"
                        fullWidth
                        error={!!errors.tier_3_adjustment}
                        helperText={errors.tier_3_adjustment?.message}
                        inputProps={{ step: 0.01, min: -1, max: 1 }}
                      />
                    )}
                  />
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Controller
                    name="below_tier_3_adjustment"
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        label="Below Tier 3"
                        type="number"
                        fullWidth
                        error={!!errors.below_tier_3_adjustment}
                        helperText={errors.below_tier_3_adjustment?.message}
                        inputProps={{ step: 0.01, min: -1, max: 1 }}
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
            <Button variant="outlined" onClick={() => navigate(`/factories/${factoryId}`)}>
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
    </Box>
  );
}
