/**
 * Dashboard Page
 *
 * Platform overview showing key metrics and quick actions.
 * This is a placeholder - full implementation in a later story.
 */

import { Box, Typography, Paper, Grid2 as Grid } from '@mui/material';
import PublicIcon from '@mui/icons-material/Public';
import AgricultureIcon from '@mui/icons-material/Agriculture';
import FactoryIcon from '@mui/icons-material/Factory';
import PeopleIcon from '@mui/icons-material/People';

/**
 * Dashboard page component.
 *
 * Shows platform overview with quick access to main entities.
 */
export function Dashboard(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Platform Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Welcome to Farmer Power Platform Administration
      </Typography>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <PublicIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            <Typography variant="h6">Regions</Typography>
            <Typography variant="body2" color="text.secondary">
              Manage geographic regions
            </Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <AgricultureIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            <Typography variant="h6">Farmers</Typography>
            <Typography variant="body2" color="text.secondary">
              View and manage farmers
            </Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <FactoryIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            <Typography variant="h6">Factories</Typography>
            <Typography variant="body2" color="text.secondary">
              Configure factories and CPs
            </Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <PeopleIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            <Typography variant="h6">Users</Typography>
            <Typography variant="body2" color="text.secondary">
              Manage platform users
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
