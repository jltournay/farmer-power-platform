import { useState, useEffect, useCallback } from 'react';
import { Box, Grid2 as Grid, Alert, Button } from '@mui/material';
import { getDocumentCosts } from '../../../api/costs';
import type { DocumentCostResponse } from '../../../api/types';
import { MetricCard } from '../components/MetricCard';

interface DocumentsTabProps {
  startDate: string;
  endDate: string;
  onExportData?: (data: Record<string, unknown>[]) => void;
}

export function DocumentsTab({ startDate, endDate, onExportData }: DocumentsTabProps): JSX.Element {
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

  // Report export data when document cost data loads
  useEffect(() => {
    if (data && onExportData) {
      onExportData([{
        total_cost_usd: data.total_cost_usd,
        total_pages: data.total_pages,
        avg_cost_per_page_usd: data.avg_cost_per_page_usd,
        document_count: data.document_count,
        period_start: data.period_start,
        period_end: data.period_end,
      }]);
    }
  }, [data, onExportData]);

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
