/**
 * Factory Detail Page
 *
 * Displays factory configuration, quality thresholds, payment policy,
 * and collection points list. Implements Story 9.3 - Factory Management (AC2).
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import AddIcon from '@mui/icons-material/Add';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import SettingsIcon from '@mui/icons-material/Settings';
import PaymentIcon from '@mui/icons-material/Payment';
import GradingIcon from '@mui/icons-material/Grading';
import PlaceIcon from '@mui/icons-material/Place';
import { PageHeader, GPSFieldWithMapAssist } from '@fp/ui-components';
import { getFactory, listRegions, type FactoryDetail as FactoryDetailType, type RegionSummary } from '@/api';
import { CollectionPointQuickAddModal } from './components/CollectionPointQuickAddModal';

/**
 * Format payment adjustment as percentage.
 */
function formatAdjustment(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(0)}%`;
}

/**
 * Get color for payment adjustment.
 */
function getAdjustmentColor(value: number): 'success' | 'warning' | 'error' | 'default' {
  if (value > 0) return 'success';
  if (value < 0) return 'error';
  return 'default';
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
 * Factory detail page component.
 */
export function FactoryDetail(): JSX.Element {
  const { factoryId } = useParams<{ factoryId: string }>();
  const navigate = useNavigate();

  // State
  const [factory, setFactory] = useState<FactoryDetailType | null>(null);
  const [regions, setRegions] = useState<RegionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quickAddOpen, setQuickAddOpen] = useState(false);

  // Region lookup map
  const regionMap = regions.reduce<Record<string, string>>((acc, r) => {
    acc[r.id] = r.name;
    return acc;
  }, {});

  // Fetch factory data
  const fetchData = useCallback(async () => {
    if (!factoryId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getFactory(factoryId);
      setFactory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load factory');
    } finally {
      setLoading(false);
    }
  }, [factoryId]);

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

  // Handle CP quick-add success
  const handleQuickAddSuccess = () => {
    setQuickAddOpen(false);
    // Refresh factory data to show new CP count
    fetchData();
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
          title="Factory"
          onBack={() => navigate('/factories')}
        />
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!factory) {
    return (
      <Box>
        <PageHeader
          title="Factory"
          onBack={() => navigate('/factories')}
        />
        <Alert severity="warning">Factory not found</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title={factory.name}
        subtitle={`Code: ${factory.code} | Region: ${regionMap[factory.region_id] ?? factory.region_id}`}
        onBack={() => navigate('/factories')}
        statusBadge={
          <Chip
            label={factory.is_active ? 'Active' : 'Inactive'}
            color={factory.is_active ? 'success' : 'default'}
            size="small"
          />
        }
        actions={[
          {
            id: 'edit',
            label: 'Edit Factory',
            icon: <EditIcon />,
            variant: 'contained',
            onClick: () => navigate(`/factories/${factoryId}/edit`),
          },
        ]}
      />

      <Grid container spacing={3}>
        {/* Left Column - Map */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Factory Location
            </Typography>
            <GPSFieldWithMapAssist
              value={{
                lat: factory.location.latitude,
                lng: factory.location.longitude,
              }}
              onChange={() => {}} // Read-only
              disabled={true}
            />
            {factory.location.altitude_meters !== undefined && factory.location.altitude_meters !== 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Altitude: {factory.location.altitude_meters.toFixed(0)}m (from Google Elevation API)
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* Right Column - Details */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Basic Info */}
            <SectionCard title="Factory Information" icon={<LocationOnIcon color="primary" />}>
              <InfoRow label="Factory ID" value={factory.id} />
              <InfoRow label="Name" value={factory.name} />
              <InfoRow label="Code" value={factory.code} />
              <InfoRow label="Region" value={regionMap[factory.region_id] ?? factory.region_id} />
              <Divider sx={{ my: 1 }} />
              <InfoRow
                label="Location"
                value={`${factory.location.latitude.toFixed(4)}, ${factory.location.longitude.toFixed(4)}`}
              />
              <InfoRow
                label="Processing Capacity"
                value={`${factory.processing_capacity_kg.toLocaleString()} kg/day`}
              />
              <Divider sx={{ my: 1 }} />
              <InfoRow label="Collection Points" value={factory.collection_point_count} />
              <InfoRow label="Farmers" value={factory.farmer_count} />
            </SectionCard>

            {/* Contact Info */}
            <SectionCard title="Contact" icon={<SettingsIcon color="primary" />}>
              <InfoRow label="Phone" value={factory.contact.phone || '—'} />
              <InfoRow label="Email" value={factory.contact.email || '—'} />
              <InfoRow label="Address" value={factory.contact.address || '—'} />
            </SectionCard>
          </Box>
        </Grid>

        {/* Quality Thresholds */}
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionCard title="Quality Thresholds" icon={<GradingIcon color="primary" />}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Minimum Primary % required for each tier
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Chip label="Premium" color="success" size="small" sx={{ width: 100 }} />
                <Typography variant="body1" fontWeight={500}>
                  {factory.quality_thresholds.tier_1}%+
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Chip label="Standard" color="warning" size="small" sx={{ width: 100 }} />
                <Typography variant="body1" fontWeight={500}>
                  {factory.quality_thresholds.tier_2}%+
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Chip label="Acceptable" color="info" size="small" sx={{ width: 100 }} />
                <Typography variant="body1" fontWeight={500}>
                  {factory.quality_thresholds.tier_3}%+
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Chip label="Below" color="default" size="small" sx={{ width: 100 }} />
                <Typography variant="body1" fontWeight={500}>
                  &lt;{factory.quality_thresholds.tier_3}%
                </Typography>
              </Box>
            </Box>
          </SectionCard>
        </Grid>

        {/* Payment Policy */}
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionCard title="Payment Policy" icon={<PaymentIcon color="primary" />}>
            <InfoRow
              label="Policy Type"
              value={
                <Chip
                  label={factory.payment_policy.policy_type.replace('_', ' ')}
                  size="small"
                  variant="outlined"
                />
              }
            />
            <Divider sx={{ my: 1 }} />
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Rate Adjustments by Tier
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="body2" sx={{ width: 100 }}>Premium:</Typography>
                <Chip
                  label={formatAdjustment(factory.payment_policy.tier_1_adjustment)}
                  color={getAdjustmentColor(factory.payment_policy.tier_1_adjustment)}
                  size="small"
                />
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="body2" sx={{ width: 100 }}>Standard:</Typography>
                <Chip
                  label={formatAdjustment(factory.payment_policy.tier_2_adjustment)}
                  color={getAdjustmentColor(factory.payment_policy.tier_2_adjustment)}
                  size="small"
                />
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="body2" sx={{ width: 100 }}>Acceptable:</Typography>
                <Chip
                  label={formatAdjustment(factory.payment_policy.tier_3_adjustment)}
                  color={getAdjustmentColor(factory.payment_policy.tier_3_adjustment)}
                  size="small"
                />
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="body2" sx={{ width: 100 }}>Below:</Typography>
                <Chip
                  label={formatAdjustment(factory.payment_policy.below_tier_3_adjustment)}
                  color={getAdjustmentColor(factory.payment_policy.below_tier_3_adjustment)}
                  size="small"
                />
              </Box>
            </Box>
          </SectionCard>
        </Grid>

        {/* Grading Model */}
        {factory.grading_model && (
          <Grid size={12}>
            <SectionCard title="Grading Model" icon={<GradingIcon color="primary" />}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">
                    Model ID
                  </Typography>
                  <Typography variant="body1">{factory.grading_model.id}</Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">
                    Name
                  </Typography>
                  <Typography variant="body1">{factory.grading_model.name}</Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">
                    Version
                  </Typography>
                  <Typography variant="body1">{factory.grading_model.version}</Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">
                    Grade Count
                  </Typography>
                  <Typography variant="body1">{factory.grading_model.grade_count}</Typography>
                </Grid>
              </Grid>
            </SectionCard>
          </Grid>
        )}

        {/* Collection Points */}
        <Grid size={12}>
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <PlaceIcon color="primary" />
                  <Typography variant="h6" component="h2">
                    Collection Points ({factory.collection_point_count})
                  </Typography>
                </Box>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  size="small"
                  onClick={() => setQuickAddOpen(true)}
                >
                  Add Collection Point
                </Button>
              </Box>

              {factory.collection_point_count === 0 ? (
                <Alert severity="info">
                  No collection points yet. Add a collection point to start receiving deliveries.
                </Alert>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>ID</TableCell>
                        <TableCell align="center">Farmers</TableCell>
                        <TableCell align="center">Status</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {/* Placeholder - would fetch CPs separately in real impl */}
                      <TableRow>
                        <TableCell colSpan={5} sx={{ textAlign: 'center', py: 3 }}>
                          <Typography variant="body2" color="text.secondary">
                            Collection points will be listed here. View count: {factory.collection_point_count}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Collection Point Quick-Add Modal */}
      <CollectionPointQuickAddModal
        open={quickAddOpen}
        onClose={() => setQuickAddOpen(false)}
        onSuccess={handleQuickAddSuccess}
        factoryId={factory.id}
        regionId={factory.region_id}
      />
    </Box>
  );
}
