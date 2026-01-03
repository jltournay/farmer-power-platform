/**
 * ROI Summary Page
 *
 * Factory Owner's return on investment dashboard.
 * This is a placeholder component for Story 0.5.7.
 */

import { Box, Typography, Paper } from '@mui/material';
import BarChartIcon from '@mui/icons-material/BarChart';

/**
 * ROI Summary placeholder component.
 *
 * Will be implemented in a future story with:
 * - Quality improvement metrics
 * - Cost savings from reduced rejections
 * - Farmer performance trends
 * - Investment recommendations
 */
export function ROISummary(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        ROI Summary
      </Typography>

      <Paper
        sx={{
          p: 4,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 300,
          backgroundColor: 'background.paper',
        }}
      >
        <BarChartIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Coming Soon
        </Typography>
        <Typography variant="body2" color="text.secondary" textAlign="center">
          The ROI Summary will show return on investment metrics,
          <br />
          quality improvement trends, and cost savings analysis.
        </Typography>
      </Paper>
    </Box>
  );
}
