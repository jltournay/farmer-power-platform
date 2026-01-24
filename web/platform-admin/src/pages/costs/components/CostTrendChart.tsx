import { Box, Typography, Skeleton } from '@mui/material';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { DailyTrendEntry } from '../../../api/types';

interface CostTrendChartProps {
  entries: DailyTrendEntry[];
  loading?: boolean;
  dataAvailableFrom?: string;
}

export function CostTrendChart({ entries, loading, dataAvailableFrom }: CostTrendChartProps): JSX.Element {
  if (loading) {
    return (
      <Box sx={{ p: 2 }}>
        <Skeleton width="40%" height={24} />
        <Skeleton height={250} sx={{ mt: 1 }} variant="rectangular" />
      </Box>
    );
  }

  const chartData = entries.map((entry) => ({
    date: entry.entry_date,
    LLM: parseFloat(entry.llm_cost_usd),
    Documents: parseFloat(entry.document_cost_usd),
    Embeddings: parseFloat(entry.embedding_cost_usd),
  }));

  return (
    <Box>
      <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
        Daily Cost Trend (Stacked by Type)
      </Typography>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `$${v}`} />
          <Tooltip formatter={(value: number) => [`$${value.toFixed(2)}`, undefined]} />
          <Legend />
          <Area type="monotone" dataKey="LLM" stackId="1" stroke="#8884d8" fill="#8884d8" />
          <Area type="monotone" dataKey="Documents" stackId="1" stroke="#82ca9d" fill="#82ca9d" />
          <Area type="monotone" dataKey="Embeddings" stackId="1" stroke="#ffc658" fill="#ffc658" />
        </AreaChart>
      </ResponsiveContainer>
      {dataAvailableFrom && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
          Data available from: {dataAvailableFrom}
        </Typography>
      )}
    </Box>
  );
}
