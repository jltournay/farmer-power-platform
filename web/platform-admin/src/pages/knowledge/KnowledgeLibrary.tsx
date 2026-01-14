/**
 * Knowledge Library Page
 *
 * Displays and manages RAG documents.
 * Placeholder - full implementation in Story 9.9.
 */

import { Box, Typography, Paper } from '@mui/material';
import MenuBookIcon from '@mui/icons-material/MenuBook';

/**
 * Knowledge library page component.
 */
export function KnowledgeLibrary(): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Knowledge Library
      </Typography>
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <MenuBookIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          RAG Document Management
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Full implementation coming in Story 9.9
        </Typography>
      </Paper>
    </Box>
  );
}
