/**
 * Linked Prompts Table Component
 *
 * Displays prompts linked to an AI agent with expandable row detail.
 * Uses accordion pattern for inline prompt detail expansion.
 *
 * Implements Story 9.12c - AI Agent & Prompt Viewer UI (AC 9.12c.3, AC 9.12c.4).
 */

import { useState } from 'react';
import {
  Box,
  Chip,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import type { PromptSummary } from '@/types/agent-config';
import { getStatusLabel, getStatusColor, formatDate } from '@/types/agent-config';
import { PromptDetailExpansion } from './PromptDetailExpansion';

export interface LinkedPromptsTableProps {
  /** List of prompts to display */
  prompts: PromptSummary[];
}

/**
 * Linked prompts table with expandable rows.
 */
export function LinkedPromptsTable({ prompts }: LinkedPromptsTableProps): JSX.Element {
  const [expandedPromptId, setExpandedPromptId] = useState<string | null>(null);

  const handleAccordionChange = (promptId: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedPromptId(isExpanded ? promptId : null);
  };

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {prompts.length} linked prompt{prompts.length !== 1 ? 's' : ''}
      </Typography>

      {/* Table Header */}
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>Prompt ID</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Version</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Author</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Updated</TableCell>
            </TableRow>
          </TableHead>
        </Table>
      </TableContainer>

      {/* Accordion List */}
      {prompts.map((prompt) => (
        <Accordion
          key={prompt.id}
          expanded={expandedPromptId === prompt.id}
          onChange={handleAccordionChange(prompt.id)}
          sx={{
            boxShadow: 'none',
            border: '1px solid',
            borderColor: 'divider',
            '&:not(:last-child)': { borderBottom: 0 },
            '&:before': { display: 'none' },
            '&.Mui-expanded': {
              margin: 0,
            },
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{
              minHeight: 48,
              '& .MuiAccordionSummary-content': {
                margin: '8px 0',
              },
            }}
          >
            {/* Summary Row */}
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr 1fr 1fr 1.5fr',
                width: '100%',
                alignItems: 'center',
                gap: 1,
                pr: 2,
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {prompt.prompt_id}
              </Typography>
              <Typography variant="body2">{prompt.version}</Typography>
              <Box>
                <Chip
                  label={getStatusLabel(prompt.status)}
                  size="small"
                  color={getStatusColor(prompt.status)}
                  aria-label={`Status: ${getStatusLabel(prompt.status)}`}
                />
              </Box>
              <Typography variant="body2">{prompt.author || '—'}</Typography>
              <Typography variant="body2" color="text.secondary">
                {formatDate(prompt.updated_at)}
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails sx={{ bgcolor: 'grey.50', borderTop: 1, borderColor: 'divider' }}>
            <PromptDetailExpansion prompt={prompt} />
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}
