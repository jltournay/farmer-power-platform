import { Box, LinearProgress, Typography, Skeleton } from '@mui/material';

interface BudgetBarProps {
  label: string;
  utilization: number;
  current: string;
  threshold: string;
  loading?: boolean;
}

function getUtilizationColor(percent: number): 'success' | 'warning' | 'error' {
  if (percent >= 90) return 'error';
  if (percent >= 75) return 'warning';
  return 'success';
}

export function BudgetBar({ label, utilization, current, threshold, loading }: BudgetBarProps): JSX.Element {
  if (loading) {
    return (
      <Box sx={{ mb: 2 }}>
        <Skeleton width="40%" height={16} />
        <Skeleton height={8} sx={{ mt: 1, borderRadius: 1 }} />
        <Skeleton width="60%" height={14} sx={{ mt: 0.5 }} />
      </Box>
    );
  }

  const color = getUtilizationColor(utilization);
  const clampedUtilization = Math.min(utilization, 100);

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
        <Typography variant="body2" fontWeight={600}>
          {label}
        </Typography>
        <Typography variant="body2" color={`${color}.main`} fontWeight={600}>
          {utilization.toFixed(0)}%
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={clampedUtilization}
        color={color}
        sx={{ height: 8, borderRadius: 1 }}
      />
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
        ${current} / ${threshold}
      </Typography>
    </Box>
  );
}
