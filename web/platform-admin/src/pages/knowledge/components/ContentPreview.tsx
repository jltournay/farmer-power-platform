/**
 * Content Preview Component
 *
 * Displays extracted markdown content in a scrollable preview panel.
 * Story 9.9b (AC 9.9b.3, AC 9.9b.6)
 */

import { Box, Paper, Typography } from '@mui/material';

interface ContentPreviewProps {
  content: string;
  maxHeight?: number;
}

/**
 * Renders document content in a scrollable panel with pre-formatted whitespace.
 */
export function ContentPreview({ content, maxHeight = 400 }: ContentPreviewProps): JSX.Element {
  if (!content) {
    return (
      <Paper variant="outlined" sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No content available
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        maxHeight,
        overflow: 'auto',
        bgcolor: 'grey.50',
      }}
    >
      <Box
        component="pre"
        sx={{
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontFamily: 'monospace',
          fontSize: '0.85rem',
          lineHeight: 1.6,
          m: 0,
        }}
      >
        {content}
      </Box>
    </Paper>
  );
}
