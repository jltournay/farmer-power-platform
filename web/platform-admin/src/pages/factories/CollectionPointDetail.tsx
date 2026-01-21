/**
 * Collection Point Detail Page
 *
 * Displays collection point configuration within a factory hierarchy.
 * Implements Story 9.4 - Collection Point Management (AC1, AC5, AC6, AC7).
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
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
  Button,
  Divider,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import PersonIcon from '@mui/icons-material/Person';
import PeopleIcon from '@mui/icons-material/People';
import InventoryIcon from '@mui/icons-material/Inventory';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import { PageHeader, GPSFieldWithMapAssist } from '@fp/ui-components';
import {
  getCollectionPoint,
  getFactory,
  type CollectionPointDetailFull,
  type FactoryDetail,
  parseTimeRange,
} from '@/api';

/**
 * Status badge color mapping.
 */
function getStatusColor(status: string): 'success' | 'default' | 'warning' {
  switch (status) {
    case 'active':
      return 'success';
    case 'inactive':
      return 'default';
    case 'seasonal':
      return 'warning';
    default:
      return 'default';
  }
}

/**
 * Status badge icon mapping.
 */
function getStatusIcon(status: string): string {
  switch (status) {
    case 'active':
      return '●';
    case 'inactive':
      return '○';
    case 'seasonal':
      return '◐';
    default:
      return '○';
  }
}

/**
 * Format collection days as badges.
 */
function formatCollectionDays(days: string[]): string[] {
  const dayLabels: Record<string, string> = {
    mon: 'Mon',
    tue: 'Tue',
    wed: 'Wed',
    thu: 'Thu',
    fri: 'Fri',
    sat: 'Sat',
    sun: 'Sun',
  };
  return days.map((d) => dayLabels[d] ?? d);
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
    <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
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
    <Box sx={{ py: 1 }}>
      <Typography variant="caption" color="text.secondary" display="block">
        {label}
      </Typography>
      <Typography variant="body2" fontWeight={500}>
        {value}
      </Typography>
    </Box>
  );
}

/**
 * Collection point detail page component.
 */
export function CollectionPointDetail(): JSX.Element {
  const { factoryId, cpId } = useParams<{ factoryId: string; cpId: string }>();
  const navigate = useNavigate();

  // State
  const [cp, setCp] = useState<CollectionPointDetailFull | null>(null);
  const [factory, setFactory] = useState<FactoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    } catch (err) {
      if (err instanceof Error) {
        // Check for 404
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
  }, [cpId, factoryId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
          title="Collection Point"
          onBack={() => navigate(`/factories/${factoryId}`)}
        />
        <Alert
          severity="error"
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => navigate(`/factories/${factoryId}`)}
            >
              Back to Factory
            </Button>
          }
        >
          {error}
        </Alert>
      </Box>
    );
  }

  if (!cp || !factory) {
    return (
      <Box>
        <PageHeader
          title="Collection Point"
          onBack={() => navigate(`/factories/${factoryId}`)}
        />
        <Alert severity="warning">Collection point data not available</Alert>
      </Box>
    );
  }

  const weekdayHours = parseTimeRange(cp.operating_hours.weekdays);
  const weekendHours = parseTimeRange(cp.operating_hours.weekends);
  const collectionDayLabels = formatCollectionDays(cp.collection_days);

  return (
    <Box>
      {/* Page Header with Breadcrumb */}
      <PageHeader
        title={cp.name}
        subtitle={`Factory: ${factory.name} | Region: ${cp.region_id}`}
        onBack={() => navigate(`/factories/${factoryId}`)}
        statusBadge={
          <Chip
            label={`${getStatusIcon(cp.status)} ${cp.status.charAt(0).toUpperCase() + cp.status.slice(1)}`}
            color={getStatusColor(cp.status)}
            size="small"
          />
        }
        actions={[
          {
            id: 'edit',
            label: 'Edit',
            icon: <EditIcon />,
            variant: 'contained',
            onClick: () => navigate(`/factories/${factoryId}/collection-points/${cpId}/edit`),
          },
        ]}
      />

      <Grid container spacing={3}>
        {/* Basic Information */}
        <Grid size={12}>
          <SectionCard title="Collection Point Information" icon={<LocationOnIcon color="primary" />}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <InfoRow label="ID" value={cp.id} />
                <InfoRow label="Name" value={cp.name} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <InfoRow
                  label="Status"
                  value={
                    <Chip
                      label={`${getStatusIcon(cp.status)} ${cp.status}`}
                      color={getStatusColor(cp.status)}
                      size="small"
                    />
                  }
                />
                <InfoRow
                  label="Factory"
                  value={
                    <RouterLink to={`/factories/${factoryId}`} style={{ color: 'inherit' }}>
                      {factory.name}
                    </RouterLink>
                  }
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <InfoRow label="Region" value={cp.region_id} />
                <InfoRow
                  label="Location"
                  value={`${cp.location.latitude.toFixed(4)}, ${cp.location.longitude.toFixed(4)}`}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <InfoRow label="Farmers" value={cp.farmer_count} />
                <InfoRow
                  label="Created"
                  value={new Date(cp.created_at).toLocaleDateString()}
                />
              </Grid>
            </Grid>
          </SectionCard>
        </Grid>

        {/* Map - Left Column */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom>
              Collection Point Location
            </Typography>
            <GPSFieldWithMapAssist
              value={{
                lat: cp.location.latitude,
                lng: cp.location.longitude,
              }}
              onChange={() => {}} // Read-only
              disabled={true}
            />
          </Paper>
        </Grid>

        {/* Clerk Info - Right Column */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <SectionCard title="Clerk Assignment" icon={<PersonIcon color="primary" />}>
            {cp.clerk_id ? (
              <>
                <InfoRow label="Clerk ID" value={cp.clerk_id} />
                <InfoRow label="Clerk Phone" value={cp.clerk_phone ?? '—'} />
              </>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                No clerk assigned
              </Typography>
            )}
          </SectionCard>
        </Grid>

        {/* Operating Hours */}
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionCard title="Operating Hours" icon={<AccessTimeIcon color="primary" />}>
            <Grid container spacing={2}>
              <Grid size={6}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Weekdays
                </Typography>
                <Typography variant="body1" fontWeight={500}>
                  {weekdayHours.start} - {weekdayHours.end}
                </Typography>
              </Grid>
              <Grid size={6}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Weekends
                </Typography>
                <Typography variant="body1" fontWeight={500}>
                  {weekendHours.start} - {weekendHours.end}
                </Typography>
              </Grid>
            </Grid>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Collection Days
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => (
                <Chip
                  key={day}
                  label={day}
                  size="small"
                  color={collectionDayLabels.includes(day) ? 'primary' : 'default'}
                  variant={collectionDayLabels.includes(day) ? 'filled' : 'outlined'}
                />
              ))}
            </Box>
          </SectionCard>
        </Grid>

        {/* Capacity & Equipment */}
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionCard title="Capacity & Equipment" icon={<InventoryIcon color="primary" />}>
            <InfoRow
              label="Max Daily Capacity"
              value={`${cp.capacity.max_daily_kg.toLocaleString()} kg`}
            />
            <InfoRow
              label="Storage Type"
              value={cp.capacity.storage_type.replace('_', ' ')}
            />
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Equipment
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                {cp.capacity.has_weighing_scale ? (
                  <CheckCircleIcon color="success" fontSize="small" />
                ) : (
                  <CancelIcon color="disabled" fontSize="small" />
                )}
                <Typography variant="body2">Weighing Scale</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                {cp.capacity.has_qc_device ? (
                  <CheckCircleIcon color="success" fontSize="small" />
                ) : (
                  <CancelIcon color="disabled" fontSize="small" />
                )}
                <Typography variant="body2">QC Device</Typography>
              </Box>
            </Box>
          </SectionCard>
        </Grid>

        {/* Related Data */}
        <Grid size={12}>
          <SectionCard title="Related Data" icon={<PeopleIcon color="primary" />}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="body1">
                <strong>{cp.farmer_count}</strong> farmer{cp.farmer_count !== 1 ? 's' : ''} have this as their primary collection point
              </Typography>
              <Button
                component={RouterLink}
                to={`/farmers?collection_point_id=${cp.id}`}
                variant="outlined"
                size="small"
                startIcon={<ArrowBackIcon sx={{ transform: 'rotate(180deg)' }} />}
              >
                View Farmers
              </Button>
            </Box>
            {cp.lead_farmer && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Lead Farmer
                </Typography>
                <Box sx={{ display: 'flex', gap: 3 }}>
                  <Typography variant="body2">
                    <strong>Name:</strong> {cp.lead_farmer.name}
                  </Typography>
                  <Typography variant="body2">
                    <strong>ID:</strong> {cp.lead_farmer.id}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Phone:</strong> {cp.lead_farmer.phone}
                  </Typography>
                </Box>
              </>
            )}
          </SectionCard>
        </Grid>
      </Grid>
    </Box>
  );
}
