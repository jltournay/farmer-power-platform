/**
 * Collection Point Quick-Add Modal
 *
 * Modal form for quickly adding a collection point from the factory detail page.
 * Implements Story 9.3 - Factory Management (AC6).
 */

import { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Grid2 as Grid,
  Alert,
  CircularProgress,
  Typography,
  Snackbar,
} from '@mui/material';
import { GPSFieldWithMapAssist, type GPSCoordinates } from '@fp/ui-components';
import { createCollectionPoint, type CollectionPointCreateRequest, type GeoLocation } from '@/api';

// ============================================================================
// Types
// ============================================================================

interface CollectionPointQuickAddModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  factoryId: string;
  regionId: string;
}

// ============================================================================
// Validation Schema
// ============================================================================

const quickAddSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
  clerk_id: z.string().max(50).optional(),
  clerk_phone: z.string().max(20).optional(),
});

type FormValues = z.infer<typeof quickAddSchema>;

const DEFAULT_VALUES: Partial<FormValues> = {
  name: '',
  // GPS coordinates start empty - user must set them explicitly
  clerk_id: '',
  clerk_phone: '',
};

// ============================================================================
// Component
// ============================================================================

export function CollectionPointQuickAddModal({
  open,
  onClose,
  onSuccess,
  factoryId,
  regionId,
}: CollectionPointQuickAddModalProps): JSX.Element {
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successSnackbar, setSuccessSnackbar] = useState(false);

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(quickAddSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const latitude = watch('latitude');
  const longitude = watch('longitude');

  // Handle GPS change from map
  const handleGPSChange = (coords: GPSCoordinates) => {
    if (coords.lat !== null) setValue('latitude', coords.lat);
    if (coords.lng !== null) setValue('longitude', coords.lng);
  };

  // Handle close
  const handleClose = () => {
    reset(DEFAULT_VALUES);
    setSubmitError(null);
    onClose();
  };

  // Form submission
  const onSubmit = async (data: FormValues) => {
    setSubmitError(null);

    try {
      const location: GeoLocation = {
        latitude: data.latitude,
        longitude: data.longitude,
      };

      const request: CollectionPointCreateRequest = {
        name: data.name,
        location,
        region_id: regionId,
        clerk_id: data.clerk_id || undefined,
        clerk_phone: data.clerk_phone || undefined,
        status: 'active',
      };

      await createCollectionPoint(factoryId, request);
      setSuccessSnackbar(true);
      reset(DEFAULT_VALUES);
      // Call onSuccess after brief delay to show snackbar
      setTimeout(() => {
        setSuccessSnackbar(false);
        onSuccess();
      }, 1000);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create collection point');
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Collection Point</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          {submitError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setSubmitError(null)}>
              {submitError}
            </Alert>
          )}

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Create a new collection point for this factory. The collection point will be
            automatically assigned to the factory&apos;s region.
          </Typography>

          <Grid container spacing={2}>
            <Grid size={12}>
              <Controller
                name="name"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Collection Point Name"
                    fullWidth
                    required
                    error={!!errors.name}
                    helperText={errors.name?.message || 'e.g., Kapkatet CP'}
                  />
                )}
              />
            </Grid>

            <Grid size={12}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Location
              </Typography>
              <GPSFieldWithMapAssist
                value={{ lat: latitude ?? null, lng: longitude ?? null }}
                onChange={handleGPSChange}
                initialExpanded
              />
            </Grid>

            <Grid size={6}>
              <Controller
                name="clerk_id"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Clerk ID (Optional)"
                    fullWidth
                    error={!!errors.clerk_id}
                    helperText={errors.clerk_id?.message}
                  />
                )}
              />
            </Grid>

            <Grid size={6}>
              <Controller
                name="clerk_phone"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Clerk Phone (Optional)"
                    fullWidth
                    error={!!errors.clerk_phone}
                    helperText={errors.clerk_phone?.message}
                  />
                )}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting}
            startIcon={isSubmitting ? <CircularProgress size={20} color="inherit" /> : undefined}
          >
            {isSubmitting ? 'Creating...' : 'Create Collection Point'}
          </Button>
        </DialogActions>
      </form>

      {/* Success Snackbar (AC7) */}
      <Snackbar
        open={successSnackbar}
        autoHideDuration={3000}
        onClose={() => setSuccessSnackbar(false)}
        message="Collection point created successfully"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Dialog>
  );
}
