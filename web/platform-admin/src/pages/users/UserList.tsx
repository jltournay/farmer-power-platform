/**
 * User List Page
 *
 * Displays all platform users.
 * Placeholder - full implementation in Story 9.7.
 */

import { Box, Typography, Paper } from '@mui/material';
import PeopleIcon from '@mui/icons-material/People';

/**
 * User list page component.
 */
export function UserList(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Users
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <PeopleIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          User Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.7
        </Typography>
      </Paper>
    </Box>
  );
}
