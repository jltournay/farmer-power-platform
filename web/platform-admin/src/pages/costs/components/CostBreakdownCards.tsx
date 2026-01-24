import { Grid2 as Grid, Card, CardContent, Typography, Skeleton, Box } from '@mui/material';
import type { CostTypeBreakdown } from '../../../api/types';

interface CostBreakdownCardsProps {
  breakdown: CostTypeBreakdown[];
  loading?: boolean;
}

function getCostTypeLabel(costType: string): string {
  switch (costType) {
    case 'llm': return 'LLM (OpenRouter)';
    case 'document': return 'Documents (Azure)';
    case 'embedding': return 'Embeddings (Pinecone)';
    case 'sms': return 'SMS';
    default: return costType;
  }
}

export function CostBreakdownCards({ breakdown, loading }: CostBreakdownCardsProps): JSX.Element {
  if (loading) {
    return (
      <Grid container spacing={2}>
        {[0, 1, 2].map((i) => (
          <Grid size={{ xs: 12, sm: 4 }} key={i}>
            <Card>
              <CardContent>
                <Skeleton width="60%" height={16} />
                <Skeleton width="80%" height={28} sx={{ mt: 1 }} />
                <Skeleton width="50%" height={14} sx={{ mt: 0.5 }} />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  }

  return (
    <Box>
      <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
        Cost by Type
      </Typography>
      <Grid container spacing={2}>
        {breakdown.map((item) => (
          <Grid size={{ xs: 12, sm: 4 }} key={item.cost_type}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase' }}>
                  {getCostTypeLabel(item.cost_type)}
                </Typography>
                <Typography variant="h6" fontWeight={700} sx={{ mt: 0.5 }}>
                  ${parseFloat(item.total_cost_usd).toFixed(2)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.request_count.toLocaleString()} requests &middot; {item.percentage.toFixed(0)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
