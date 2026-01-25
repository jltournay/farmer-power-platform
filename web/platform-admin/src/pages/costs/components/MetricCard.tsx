import { Card, CardContent, Typography, Skeleton, Box } from '@mui/material';

interface MetricCardProps {
  label: string;
  value: string;
  subtitle?: string;
  loading?: boolean;
  error?: boolean;
}

export function MetricCard({ label, value, subtitle, loading, error }: MetricCardProps): JSX.Element {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Skeleton width="60%" height={20} />
          <Skeleton width="80%" height={36} sx={{ mt: 1 }} />
          <Skeleton width="50%" height={16} sx={{ mt: 0.5 }} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 600 }}>
          {label}
        </Typography>
        <Box sx={{ mt: 1 }}>
          <Typography variant="h5" component="div" fontWeight={700} color={error ? 'error.main' : 'text.primary'}>
            {value}
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, minHeight: '1.5em' }}>
          {subtitle || '\u00A0'}
        </Typography>
      </CardContent>
    </Card>
  );
}
