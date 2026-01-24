import { useState, useEffect, useCallback } from 'react';
import { Box, Grid2 as Grid, Alert, Button, Typography, Skeleton } from '@mui/material';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import { getEmbeddingsByDomain } from '../../../api/costs';
import type { EmbeddingByDomainResponse } from '../../../api/types';
import { MetricCard } from '../components/MetricCard';

interface EmbeddingsTabProps {
  startDate: string;
  endDate: string;
}

export function EmbeddingsTab({ startDate, endDate }: EmbeddingsTabProps): JSX.Element {
  const [data, setData] = useState<EmbeddingByDomainResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getEmbeddingsByDomain({ start_date: startDate, end_date: endDate });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load embedding costs');
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

  const totalTexts = data?.domain_costs.reduce((sum, d) => sum + d.texts_count, 0) ?? 0;
  const totalTokens = data?.domain_costs.reduce((sum, d) => sum + d.tokens_total, 0) ?? 0;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Summary Cards */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <MetricCard
            label="Embedding Total"
            value={data ? `$${parseFloat(data.total_embedding_cost_usd).toFixed(2)}` : '-'}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <MetricCard
            label="Texts Embedded"
            value={totalTexts.toLocaleString()}
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <MetricCard
            label="Total Tokens"
            value={totalTokens >= 1000000
              ? `${(totalTokens / 1000000).toFixed(1)}M`
              : totalTokens >= 1000
              ? `${(totalTokens / 1000).toFixed(0)}K`
              : totalTokens.toLocaleString()}
            loading={loading}
          />
        </Grid>
      </Grid>

      {/* Domain Table */}
      <Box>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
          Cost by Knowledge Domain
        </Typography>
        {loading ? (
          <Skeleton variant="rectangular" height={200} />
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Domain</TableCell>
                  <TableCell align="right">Texts</TableCell>
                  <TableCell align="right">Tokens</TableCell>
                  <TableCell align="right">Cost</TableCell>
                  <TableCell align="right">%</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data?.domain_costs.map((row) => (
                  <TableRow key={row.knowledge_domain}>
                    <TableCell>{row.knowledge_domain}</TableCell>
                    <TableCell align="right">{row.texts_count.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.tokens_total.toLocaleString()}</TableCell>
                    <TableCell align="right">${parseFloat(row.cost_usd).toFixed(2)}</TableCell>
                    <TableCell align="right">{row.percentage.toFixed(0)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>
    </Box>
  );
}
