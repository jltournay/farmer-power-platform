import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Alert,
  CircularProgress,
} from '@mui/material';
import { configureBudget } from '../../../api/costs';
import type { BudgetStatusResponse } from '../../../api/types';

interface BudgetConfigDialogProps {
  open: boolean;
  onClose: () => void;
  budgetStatus: BudgetStatusResponse | null;
  onSuccess: () => void;
}

export function BudgetConfigDialog({ open, onClose, budgetStatus, onSuccess }: BudgetConfigDialogProps): JSX.Element {
  const [dailyThreshold, setDailyThreshold] = useState(budgetStatus?.daily_threshold_usd ?? '');
  const [monthlyThreshold, setMonthlyThreshold] = useState(budgetStatus?.monthly_threshold_usd ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state when budgetStatus prop updates
  useEffect(() => {
    if (budgetStatus) {
      setDailyThreshold(budgetStatus.daily_threshold_usd);
      setMonthlyThreshold(budgetStatus.monthly_threshold_usd);
    }
  }, [budgetStatus]);

  const dailyValue = parseFloat(dailyThreshold);
  const monthlyValue = parseFloat(monthlyThreshold);
  const dailyValid = !isNaN(dailyValue) && dailyValue > 0;
  const monthlyValid = !isNaN(monthlyValue) && monthlyValue > 0;
  const formValid = dailyValid && monthlyValid;

  const handleSave = async () => {
    if (!formValid) return;
    setSaving(true);
    setError(null);
    try {
      await configureBudget({
        daily_threshold_usd: dailyThreshold,
        monthly_threshold_usd: monthlyThreshold,
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save budget configuration');
    } finally {
      setSaving(false);
    }
  };

  // Reset form when dialog opens with fresh data
  const handleEnter = () => {
    if (budgetStatus) {
      setDailyThreshold(budgetStatus.daily_threshold_usd);
      setMonthlyThreshold(budgetStatus.monthly_threshold_usd);
    }
    setError(null);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth TransitionProps={{ onEnter: handleEnter }}>
      <DialogTitle>Configure Budget Thresholds</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 1 }}>
          <TextField
            label="Daily Threshold (USD)"
            type="number"
            value={dailyThreshold}
            onChange={(e) => setDailyThreshold(e.target.value)}
            error={dailyThreshold !== '' && !dailyValid}
            helperText={dailyThreshold !== '' && !dailyValid ? 'Must be greater than 0' : ''}
            slotProps={{ input: { startAdornment: <Box component="span" sx={{ mr: 0.5 }}>$</Box> } }}
            fullWidth
          />
          <TextField
            label="Monthly Threshold (USD)"
            type="number"
            value={monthlyThreshold}
            onChange={(e) => setMonthlyThreshold(e.target.value)}
            error={monthlyThreshold !== '' && !monthlyValid}
            helperText={monthlyThreshold !== '' && !monthlyValid ? 'Must be greater than 0' : ''}
            slotProps={{ input: { startAdornment: <Box component="span" sx={{ mr: 0.5 }}>$</Box> } }}
            fullWidth
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={!formValid || saving}>
          {saving ? <CircularProgress size={20} /> : 'Save Thresholds'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
