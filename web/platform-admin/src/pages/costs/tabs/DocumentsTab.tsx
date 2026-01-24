import { useState, useEffect, useCallback } from 'react';
import { Box, Grid, Alert, Button } from '@mui/material';
import { getDocumentCosts } from '../../../api/costs';
import type { DocumentCostResponse } from '../../../api/types';
import { MetricCard } from '../components/MetricCard';

interface DocumentsTabProps {
  startDate: string;
  endDate: string;
}

export function DocumentsTab({ startDate, endDate }: DocumentsTabProps): JSX.Element {
  const [data, setData] = useState<DocumentCostResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDocumentCosts({ start_date: startDate, end_date: endDate });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document costs');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (error) {
    return (
      <Alert severity="error" action={<Button size="small" onClick={fetchData}>Retry</Button>}>
        {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 3 }}>
          <MetricCard
            label="Document Total"
            value={data ? `$${parseFloat(data.total_cost_usd).toFixed(2)}` : '-'}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 3 }}>
          <MetricCard
            label="Pages Processed"
            value={data ? data.total_pages.toLocaleString() : '-'}
            subtitle={data ? `${data.document_count} documents` : undefined}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 3 }}>
          <MetricCard
            label="Avg Cost/Page"
            value={data ? `$${parseFloat(data.avg_cost_per_page_usd).toFixed(3)}` : '-'}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 3 }}>
          <MetricCard
            label="Documents"
            value={data ? data.document_count.toLocaleString() : '-'}
            subtitle={data ? `${data.period_start} to ${data.period_end}` : undefined}
            loading={loading}
          />
        </Grid>
      </Grid>
    </Box>
  );
}
