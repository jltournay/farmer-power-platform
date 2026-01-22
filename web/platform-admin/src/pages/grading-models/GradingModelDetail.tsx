/**
 * Grading Model Detail Page
 *
 * Displays full grading model configuration including attributes, rules,
 * labels, and factory assignments. Read-only with factory assignment action.
 * Implements Story 9.6b - Grading Model Management UI (AC 9.6b.2, AC 9.6b.3, AC 9.6b.4).
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddIcon from '@mui/icons-material/Add';
import FactoryIcon from '@mui/icons-material/Factory';
import BlockIcon from '@mui/icons-material/Block';
import WarningIcon from '@mui/icons-material/Warning';
import { PageHeader } from '@fp/ui-components';
import {
  getGradingModel,
  type GradingModelDetailResponse,
  getGradingTypeLabel,
  getGradingTypeColor,
} from '@/api';
import { AssignFactoryDialog } from './components/AssignFactoryDialog';

/**
 * Grading model detail page component.
 */
export function GradingModelDetail(): JSX.Element {
  const { modelId } = useParams<{ modelId: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<GradingModelDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);

  const fetchData = useCallback(async () => {
    if (!modelId) return;
    setLoading(true);
    setError(null);

    try {
      const response = await getGradingModel(modelId);
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load grading model');
    } finally {
      setLoading(false);
    }
  }, [modelId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAssignSuccess = (updatedModel: GradingModelDetailResponse) => {
    setData(updatedModel);
    setAssignDialogOpen(false);
  };

  // Loading state
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  // Error state
  if (error) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/grading-models')}
          sx={{ mb: 2 }}
        >
          Back to Grading Models
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  // Not found state
  if (!data) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/grading-models')}
          sx={{ mb: 2 }}
        >
          Back to Grading Models
        </Button>
        <Alert severity="warning">Grading model not found</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title={data.model_id}
        subtitle={`${data.crops_name} - ${data.market_name}`}
        onBack={() => navigate('/grading-models')}
        statusBadge={
          <Chip
            label={getGradingTypeLabel(data.grading_type)}
            color={getGradingTypeColor(data.grading_type)}
            size="small"
            aria-label={`Grading type: ${getGradingTypeLabel(data.grading_type)}`}
          />
        }
      />

      {/* Model Information Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Model Information
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Model ID</Typography>
            <Typography variant="body1">{data.model_id}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Version</Typography>
            <Typography variant="body1">{data.model_version}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Regulatory Authority</Typography>
            <Typography variant="body1">{data.regulatory_authority}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Grading Type</Typography>
            <Chip
              label={getGradingTypeLabel(data.grading_type)}
              color={getGradingTypeColor(data.grading_type)}
              size="small"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Crops</Typography>
            <Typography variant="body1">{data.crops_name}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Market</Typography>
            <Typography variant="body1">{data.market_name}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Created</Typography>
            <Typography variant="body1">{new Date(data.created_at).toLocaleDateString()}</Typography>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">Updated</Typography>
            <Typography variant="body1">{new Date(data.updated_at).toLocaleDateString()}</Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Grading Attributes Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Grading Attributes
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Attribute</TableCell>
                <TableCell align="right">Classes</TableCell>
                <TableCell>Class Names</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(data.attributes).map(([name, attr]) => (
                <TableRow key={name}>
                  <TableCell component="th" scope="row">
                    <Typography variant="body2" fontWeight="medium">
                      {name.replace(/_/g, ' ')}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">{attr.num_classes}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {attr.classes.map((cls) => (
                        <Chip key={cls} label={cls.replace(/_/g, ' ')} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Grade Rules Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Grade Rules
        </Typography>

        {/* Reject Conditions */}
        {Object.keys(data.grade_rules.reject_conditions).length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="error.main" gutterBottom>
              Always Reject
            </Typography>
            <List dense disablePadding>
              {Object.entries(data.grade_rules.reject_conditions).map(([attr, values]) =>
                values.map((val) => (
                  <ListItem key={`${attr}-${val}`} disableGutters>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <BlockIcon fontSize="small" color="error" />
                    </ListItemIcon>
                    <ListItemText
                      primary={`${attr.replace(/_/g, ' ')} = ${val.replace(/_/g, ' ')}`}
                    />
                  </ListItem>
                ))
              )}
            </List>
          </Box>
        )}

        {/* Conditional Reject */}
        {data.grade_rules.conditional_reject.length > 0 && (
          <Box>
            <Typography variant="subtitle2" color="warning.main" gutterBottom>
              Conditional Reject
            </Typography>
            <List dense disablePadding>
              {data.grade_rules.conditional_reject.map((rule, idx) => (
                <ListItem key={idx} disableGutters>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <WarningIcon fontSize="small" color="warning" />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      `IF ${rule.if_attribute.replace(/_/g, ' ')} = ${rule.if_value.replace(/_/g, ' ')} ` +
                      `AND ${rule.then_attribute.replace(/_/g, ' ')} IN [${rule.reject_values.map((v) => v.replace(/_/g, ' ')).join(', ')}] → REJECT`
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {Object.keys(data.grade_rules.reject_conditions).length === 0 &&
          data.grade_rules.conditional_reject.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No rejection rules configured
            </Typography>
          )}
      </Paper>

      {/* Grade Labels Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Grade Labels
        </Typography>
        <Grid container spacing={2}>
          {Object.entries(data.grade_labels).map(([key, label]) => (
            <Grid key={key} size={{ xs: 12, sm: 6, md: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip label={key} size="small" variant="outlined" />
                <Typography variant="body2">→</Typography>
                <Typography variant="body1" fontWeight="medium">{label}</Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Factory Assignments Section */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Factories Using This Model ({data.active_at_factories.length})
          </Typography>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => setAssignDialogOpen(true)}
            size="small"
          >
            Assign to Factory
          </Button>
        </Box>

        {data.active_at_factories.length > 0 ? (
          <List dense disablePadding>
            {data.active_at_factories.map((factory) => (
              <ListItem key={factory.factory_id} disableGutters>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <FactoryIcon fontSize="small" color="action" />
                </ListItemIcon>
                <ListItemText
                  primary={factory.name}
                  secondary={factory.factory_id}
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No factories are currently using this grading model
          </Typography>
        )}
      </Paper>

      {/* Assign Factory Dialog */}
      <AssignFactoryDialog
        open={assignDialogOpen}
        onClose={() => setAssignDialogOpen(false)}
        onSuccess={handleAssignSuccess}
        modelId={data.model_id}
        assignedFactoryIds={data.active_at_factories.map((f) => f.factory_id)}
      />
    </Box>
  );
}
