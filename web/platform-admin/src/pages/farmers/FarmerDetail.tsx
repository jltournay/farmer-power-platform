/**
 * Farmer Detail Page
 *
 * Displays farmer profile, farm info, collection points, and performance summary.
 * Implements Story 9.5 - Farmer Management (AC 9.5.2).
 *
 * Features:
 * - Personal info section
 * - Farm info section with GPS
 * - Performance metrics (30d/90d)
 * - Communication preferences
 * - Deactivation action (AC 9.5.6)
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
  Card,
  CardContent,
  Divider,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Snackbar,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import PersonIcon from '@mui/icons-material/Person';
import AgricultureIcon from '@mui/icons-material/Agriculture';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import NotificationsIcon from '@mui/icons-material/Notifications';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { PageHeader, GPSFieldWithMapAssist } from '@fp/ui-components';
import {
  getFarmer,
  updateFarmer,
  listRegions,
  type FarmerDetail as FarmerDetailType,
  type RegionSummary,
  getTierColor,
  FARM_SCALE_OPTIONS,
  NOTIFICATION_CHANNEL_OPTIONS,
  INTERACTION_PREF_OPTIONS,
  LANGUAGE_OPTIONS,
} from '@/api';

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
 * Get trend icon component.
 */
function TrendIcon({ trend, size = 'small' }: { trend: string; size?: 'small' | 'medium' }): JSX.Element {
  switch (trend) {
    case 'improving':
      return <TrendingUpIcon fontSize={size} color="success" />;
    case 'declining':
      return <TrendingDownIcon fontSize={size} color="error" />;
    default:
      return <TrendingFlatIcon fontSize={size} color="disabled" />;
  }
}

/**
 * Performance metric display.
 */
function MetricCard({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: number;
  unit: string;
  color?: 'success' | 'warning' | 'error' | 'info';
}): JSX.Element {
  return (
    <Box sx={{ textAlign: 'center', p: 1 }}>
      <Typography variant="h4" color={color ? `${color}.main` : 'text.primary'} fontWeight={600}>
        {value.toFixed(value % 1 === 0 ? 0 : 1)}
        <Typography component="span" variant="body2" color="text.secondary">
          {unit}
        </Typography>
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

/**
 * Farmer detail page component.
 */
export function FarmerDetail(): JSX.Element {
  const { farmerId } = useParams<{ farmerId: string }>();
  const navigate = useNavigate();

  // State
  const [farmer, setFarmer] = useState<FarmerDetailType | null>(null);
  const [regions, setRegions] = useState<RegionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);
  const [activateDialogOpen, setActivateDialogOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [successSnackbar, setSuccessSnackbar] = useState<string | null>(null);

  // Region lookup map
  const regionMap = regions.reduce<Record<string, string>>((acc, r) => {
    acc[r.id] = r.name;
    return acc;
  }, {});

  // Fetch farmer data
  const fetchData = useCallback(async () => {
    if (!farmerId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getFarmer(farmerId);
      setFarmer(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load farmer');
    } finally {
      setLoading(false);
    }
  }, [farmerId]);

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
    fetchData();
    fetchRegions();
  }, [fetchData, fetchRegions]);

  // Handle deactivation (AC 9.5.6)
  const handleDeactivate = async () => {
    if (!farmerId) return;
    setActionLoading(true);

    try {
      await updateFarmer(farmerId, { is_active: false });
      setDeactivateDialogOpen(false);
      setSuccessSnackbar('Farmer deactivated successfully');
      fetchData(); // Refresh data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate farmer');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle activation
  const handleActivate = async () => {
    if (!farmerId) return;
    setActionLoading(true);

    try {
      await updateFarmer(farmerId, { is_active: true });
      setActivateDialogOpen(false);
      setSuccessSnackbar('Farmer activated successfully');
      fetchData(); // Refresh data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate farmer');
    } finally {
      setActionLoading(false);
    }
  };

  // Helper functions for display
  const getFarmScaleLabel = (scale: string): string => {
    const option = FARM_SCALE_OPTIONS.find((o) => o.value === scale);
    return option?.label ?? scale;
  };

  const getNotificationLabel = (channel: string): string => {
    const option = NOTIFICATION_CHANNEL_OPTIONS.find((o) => o.value === channel);
    return option?.label ?? channel;
  };

  const getInteractionLabel = (pref: string): string => {
    const option = INTERACTION_PREF_OPTIONS.find((o) => o.value === pref);
    return option?.label ?? pref;
  };

  const getLanguageLabel = (lang: string): string => {
    const option = LANGUAGE_OPTIONS.find((o) => o.value === lang);
    return option?.label ?? lang;
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
        <PageHeader title="Farmer" onBack={() => navigate('/farmers')} />
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!farmer) {
    return (
      <Box>
        <PageHeader title="Farmer" onBack={() => navigate('/farmers')} />
        <Alert severity="warning">Farmer not found</Alert>
      </Box>
    );
  }

  const fullName = `${farmer.first_name} ${farmer.last_name}`;

  return (
    <Box>
      <PageHeader
        title={fullName}
        subtitle={`ID: ${farmer.id}${farmer.grower_number ? ` | Grower #: ${farmer.grower_number}` : ''}`}
        onBack={() => navigate('/farmers')}
        statusBadge={
          <Chip
            label={farmer.is_active ? 'Active' : 'Inactive'}
            color={farmer.is_active ? 'success' : 'default'}
            size="small"
          />
        }
        actions={[
          ...(farmer.is_active
            ? [
                {
                  id: 'deactivate',
                  label: 'Deactivate',
                  icon: <BlockIcon />,
                  variant: 'outlined' as const,
                  onClick: () => setDeactivateDialogOpen(true),
                },
              ]
            : [
                {
                  id: 'activate',
                  label: 'Activate',
                  icon: <CheckCircleIcon />,
                  variant: 'outlined' as const,
                  onClick: () => setActivateDialogOpen(true),
                },
              ]),
          {
            id: 'edit',
            label: 'Edit Farmer',
            icon: <EditIcon />,
            variant: 'contained' as const,
            onClick: () => navigate(`/farmers/${farmerId}/edit`),
          },
        ]}
      />

      <Grid container spacing={3}>
        {/* Personal Information */}
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionCard title="Personal Information" icon={<PersonIcon color="primary" />}>
            <InfoRow label="Full Name" value={fullName} />
            <InfoRow label="Phone" value={farmer.phone} />
            <InfoRow label="National ID" value={farmer.national_id} />
            <InfoRow label="Farmer ID" value={farmer.id} />
            {farmer.grower_number && <InfoRow label="Grower Number" value={farmer.grower_number} />}
            <Divider sx={{ my: 1 }} />
            <InfoRow
              label="Registration Date"
              value={new Date(farmer.registration_date).toLocaleDateString()}
            />
          </SectionCard>
        </Grid>

        {/* Farm Information */}
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionCard title="Farm Information" icon={<AgricultureIcon color="primary" />}>
            <InfoRow label="Region" value={regionMap[farmer.region_id] ?? farmer.region_id} />
            <InfoRow label="Collection Point" value={farmer.collection_point_id} />
            <InfoRow label="Farm Size" value={`${farmer.farm_size_hectares.toFixed(2)} hectares`} />
            <InfoRow label="Farm Scale" value={getFarmScaleLabel(farmer.farm_scale)} />
            <Divider sx={{ my: 1 }} />
            <InfoRow
              label="Location"
              value={`${farmer.farm_location.latitude.toFixed(4)}, ${farmer.farm_location.longitude.toFixed(4)}`}
            />
          </SectionCard>
        </Grid>

        {/* Performance Metrics */}
        <Grid size={12}>
          <SectionCard
            title="Performance"
            icon={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TrendIcon trend={farmer.performance.trend} size="medium" />
              </Box>
            }
          >
            <Grid container spacing={2}>
              {/* Current Status */}
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 1 }}>
                    <Chip
                      label={farmer.performance.tier}
                      color={getTierColor(farmer.performance.tier)}
                      variant="filled"
                    />
                    <TrendIcon trend={farmer.performance.trend} />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center' }}>
                    Current Tier & Trend
                  </Typography>
                </Paper>
              </Grid>

              {/* 30-Day Performance */}
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <MetricCard
                    label="30-Day Primary %"
                    value={farmer.performance.primary_percentage_30d}
                    unit="%"
                    color={
                      farmer.performance.primary_percentage_30d >= 85
                        ? 'success'
                        : farmer.performance.primary_percentage_30d >= 70
                          ? 'warning'
                          : 'error'
                    }
                  />
                </Paper>
              </Grid>

              {/* 90-Day Performance */}
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <MetricCard
                    label="90-Day Primary %"
                    value={farmer.performance.primary_percentage_90d}
                    unit="%"
                    color={
                      farmer.performance.primary_percentage_90d >= 85
                        ? 'success'
                        : farmer.performance.primary_percentage_90d >= 70
                          ? 'warning'
                          : 'error'
                    }
                  />
                </Paper>
              </Grid>

              {/* Today's Deliveries */}
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <MetricCard
                    label="Today's Deliveries"
                    value={farmer.performance.deliveries_today}
                    unit={` (${farmer.performance.kg_today.toFixed(1)} kg)`}
                  />
                </Paper>
              </Grid>

              {/* Volume Stats */}
              <Grid size={{ xs: 12, sm: 6 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Delivery Volume
                  </Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-around' }}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight={600}>
                        {farmer.performance.total_kg_30d.toFixed(0)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        kg (30 days)
                      </Typography>
                    </Box>
                    <Divider orientation="vertical" flexItem />
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight={600}>
                        {farmer.performance.total_kg_90d.toFixed(0)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        kg (90 days)
                      </Typography>
                    </Box>
                  </Box>
                </Paper>
              </Grid>
            </Grid>
          </SectionCard>
        </Grid>

        {/* Location Map */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <LocationOnIcon color="primary" />
              <Typography variant="h6">Farm Location</Typography>
            </Box>
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
          <SectionCard title="Communication Preferences" icon={<NotificationsIcon color="primary" />}>
            <InfoRow
              label="Notification Channel"
              value={getNotificationLabel(farmer.communication_prefs.notification_channel)}
            />
            <InfoRow
              label="Information Preference"
              value={getInteractionLabel(farmer.communication_prefs.interaction_pref)}
            />
            <InfoRow label="Language" value={getLanguageLabel(farmer.communication_prefs.pref_lang)} />
          </SectionCard>
        </Grid>
      </Grid>

      {/* Deactivation Confirmation Dialog (AC 9.5.6) */}
      <Dialog open={deactivateDialogOpen} onClose={() => setDeactivateDialogOpen(false)}>
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
          <Button onClick={() => setDeactivateDialogOpen(false)} disabled={actionLoading}>
            Cancel
          </Button>
          <Button onClick={handleDeactivate} color="warning" variant="contained" disabled={actionLoading}>
            {actionLoading ? 'Deactivating...' : 'Deactivate'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Activation Confirmation Dialog */}
      <Dialog open={activateDialogOpen} onClose={() => setActivateDialogOpen(false)}>
        <DialogTitle>Activate Farmer?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to reactivate <strong>{fullName}</strong>?
            <br />
            <br />
            The farmer will be able to make deliveries again.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActivateDialogOpen(false)} disabled={actionLoading}>
            Cancel
          </Button>
          <Button onClick={handleActivate} color="success" variant="contained" disabled={actionLoading}>
            {actionLoading ? 'Activating...' : 'Activate'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={!!successSnackbar}
        autoHideDuration={3000}
        onClose={() => setSuccessSnackbar(null)}
        message={successSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
}
