/**
 * Farmer Detail Page
 *
 * Individual farmer's profile, quality history, and action plans.
 * This is a placeholder component for Story 0.5.7.
 */

import { useParams } from 'react-router-dom';
import { Box, Typography, Paper, Breadcrumbs, Link } from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import { Link as RouterLink } from 'react-router-dom';

/**
 * Farmer Detail placeholder component.
 *
 * Will be implemented in a future story with:
 * - Farmer profile information
 * - Quality event history
 * - Trend indicators
 * - Action plan recommendations
 */
export function FarmerDetail(): JSX.Element {
  const { id } = useParams<{ id: string }>();

  return (
    <Box>
      {/* Breadcrumb navigation */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          component={RouterLink}
          to="/command-center"
          underline="hover"
          color="inherit"
        >
          Command Center
        </Link>
        <Typography color="text.primary">Farmer Detail</Typography>
      </Breadcrumbs>

      <Typography variant="h4" component="h1" gutterBottom>
        Farmer Detail
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
        <PersonIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Coming Soon
        </Typography>
        <Typography variant="body2" color="text.secondary" textAlign="center">
          Farmer ID: {id}
          <br />
          <br />
          This page will display detailed farmer information,
          <br />
          quality history, and personalized action plans.
        </Typography>
      </Paper>
    </Box>
  );
}
