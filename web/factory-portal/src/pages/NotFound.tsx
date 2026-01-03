/**
 * 404 Not Found Page
 *
 * Displayed when the user navigates to an unknown route.
 */

import { Box, Typography, Button, Paper } from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HomeIcon from '@mui/icons-material/Home';
import { useNavigate } from 'react-router-dom';

/**
 * Not Found page component.
 *
 * Shows a friendly 404 message with a link back to the Command Center.
 */
export function NotFound(): JSX.Element {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate('/command-center');
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '60vh',
      }}
    >
      <Paper
        sx={{
          p: 4,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          maxWidth: 400,
          textAlign: 'center',
        }}
      >
        <ErrorOutlineIcon sx={{ fontSize: 80, color: 'warning.main', mb: 2 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          Page Not Found
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          The page you are looking for does not exist or has been moved.
        </Typography>
        <Button
          variant="contained"
          startIcon={<HomeIcon />}
          onClick={handleGoHome}
          sx={{ mt: 2 }}
        >
          Go to Command Center
        </Button>
      </Paper>
    </Box>
  );
}
