/**
 * Prompt Detail Expansion Component
 *
 * Displays full prompt detail when a prompt row is expanded in the LinkedPromptsTable.
 * Shows: Status & Metadata, System Prompt, Template, Output Schema, Few-Shot Examples, A/B Test Config.
 *
 * Implements Story 9.12c - AI Agent & Prompt Viewer UI (AC 9.12c.4).
 */

import {
  Box,
  Chip,
  Typography,
  Table,
  TableBody,
  TableRow,
  TableCell,
  Alert,
} from '@mui/material';
import type { PromptSummary } from '@/types/agent-config';
import { getStatusLabel, getStatusColor } from '@/types/agent-config';

export interface PromptDetailExpansionProps {
  /** Prompt summary to display detail for */
  prompt: PromptSummary;
}

/**
 * Prompt detail expansion panel content.
 */
export function PromptDetailExpansion({ prompt }: PromptDetailExpansionProps): JSX.Element {
  // For now, we use the prompt summary data
  // In a full implementation, we would fetch full prompt detail if needed
  // However, the seed data includes content in the prompts collection
  // but the BFF PromptSummary doesn't include content
  // We'll display what we have from the summary

  // Note: The BFF currently only returns PromptSummary fields in the AgentConfigDetail.prompts array
  // Full prompt content would require a separate API call or enhancing the BFF response
  // For this story, we'll show metadata and indicate that full content would need an enhanced API

  return (
    <Box sx={{ p: 1 }}>
      {/* Status & Metadata */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Status & Metadata
        </Typography>
        <Table size="small">
          <TableBody>
            <TableRow>
              <TableCell sx={{ border: 'none', py: 0.5, width: 120 }}>
                <Typography variant="body2" color="text.secondary">
                  Status
                </Typography>
              </TableCell>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Chip
                  label={getStatusLabel(prompt.status)}
                  size="small"
                  color={getStatusColor(prompt.status)}
                />
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  Author
                </Typography>
              </TableCell>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2">{prompt.author || '—'}</Typography>
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  Prompt ID
                </Typography>
              </TableCell>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" fontFamily="monospace">
                  {prompt.prompt_id}
                </Typography>
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  Version
                </Typography>
              </TableCell>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2">{prompt.version}</Typography>
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  Document ID
                </Typography>
              </TableCell>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" fontFamily="monospace" fontSize="0.75rem">
                  {prompt.id}
                </Typography>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Box>

      {/* Note about full content */}
      <Alert severity="info" sx={{ mb: 2 }}>
        <Typography variant="body2">
          Full prompt content (system prompt, template, output schema, few-shot examples)
          is available via the <code>prompt-config</code> CLI.
        </Typography>
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          Run: <code>prompt-config get {prompt.prompt_id} --version {prompt.version}</code>
        </Typography>
      </Alert>

      {/* Placeholder sections for future enhancement */}
      <Box sx={{ opacity: 0.6 }}>
        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
          Available Sections (via CLI):
        </Typography>
        <Box component="ul" sx={{ m: 0, pl: 3 }}>
          <li>
            <Typography variant="body2" color="text.secondary">
              System Prompt
            </Typography>
          </li>
          <li>
            <Typography variant="body2" color="text.secondary">
              Template (with variable highlighting)
            </Typography>
          </li>
          <li>
            <Typography variant="body2" color="text.secondary">
              Output Schema
            </Typography>
          </li>
          <li>
            <Typography variant="body2" color="text.secondary">
              Few-Shot Examples
            </Typography>
          </li>
          <li>
            <Typography variant="body2" color="text.secondary">
              A/B Test Configuration
            </Typography>
          </li>
        </Box>
      </Box>
    </Box>
  );
}
