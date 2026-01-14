/**
 * Cost Dashboard Page
 *
 * Displays LLM spending and cost analytics.
 * Placeholder - full implementation in Story 9.10.
 */

import { Box, Typography, Paper } from '@mui/material';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';

/**
 * Cost dashboard page component.
 */
export function CostDashboard(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Cost Dashboard
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <AttachMoneyIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          LLM Cost Analytics
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.10
        </Typography>
      </Paper>
    </Box>
  );
}
