/**
 * Assign Factory Dialog
 *
 * Modal for assigning a grading model to a factory.
 * Fetches all factories, excludes already-assigned ones, and submits assignment.
 * Implements Story 9.6b - AC 9.6b.3.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Box,
} from '@mui/material';
import {
  listFactories,
  assignGradingModelToFactory,
  type FactorySummary,
  type GradingModelDetailResponse,
} from '@/api';

interface AssignFactoryDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (updatedModel: GradingModelDetailResponse) => void;
  modelId: string;
  assignedFactoryIds: string[];
}

export function AssignFactoryDialog({
  open,
  onClose,
  onSuccess,
  modelId,
  assignedFactoryIds,
}: AssignFactoryDialogProps): JSX.Element {
  const [factories, setFactories] = useState<FactorySummary[]>([]);
  const [loadingFactories, setLoadingFactories] = useState(false);
  const [selectedFactoryId, setSelectedFactoryId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available factories when dialog opens
  const fetchFactories = useCallback(async () => {
    setLoadingFactories(true);
    try {
      const response = await listFactories({ page_size: 100, active_only: true });
      setFactories(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load factories');
    } finally {
      setLoadingFactories(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      fetchFactories();
      setSelectedFactoryId('');
      setError(null);
    }
  }, [open, fetchFactories]);

  // Filter out already-assigned factories
  const availableFactories = factories.filter(
    (f) => !assignedFactoryIds.includes(f.id)
  );

  const handleSubmit = async () => {
    if (!selectedFactoryId) return;

    setSubmitting(true);
    setError(null);

    try {
      const updatedModel = await assignGradingModelToFactory(modelId, selectedFactoryId);
      onSuccess(updatedModel);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign grading model to factory');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting) {
      setError(null);
      setSelectedFactoryId('');
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Assign Grading Model to Factory</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Select a factory to assign the grading model <strong>{modelId}</strong> to.
          Factories already using this model are excluded.
        </Typography>

        {loadingFactories ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={24} />
          </Box>
        ) : availableFactories.length === 0 ? (
          <Alert severity="info">
            All active factories are already assigned to this grading model.
          </Alert>
        ) : (
          <FormControl fullWidth sx={{ mt: 1 }}>
            <InputLabel id="factory-select-label">Factory</InputLabel>
            <Select
              labelId="factory-select-label"
              value={selectedFactoryId}
              label="Factory"
              onChange={(e) => setSelectedFactoryId(e.target.value)}
              disabled={submitting}
            >
              {availableFactories.map((factory) => (
                <MenuItem key={factory.id} value={factory.id}>
                  {factory.name} ({factory.id})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!selectedFactoryId || submitting}
          startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : undefined}
        >
          {submitting ? 'Assigning...' : 'Assign'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
