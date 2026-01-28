/**
 * Prompt Detail Expansion Component
 *
 * Displays full prompt detail when a prompt row is expanded in the LinkedPromptsTable.
 * Fetches full content from API: System Prompt, Template, Output Schema, Few-Shot Examples, A/B Test Config.
 *
 * Implements Story 9.12c - AI Agent & Prompt Viewer UI (AC 9.12c.4).
 */

import { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Chip,
  Typography,
  Table,
  TableBody,
  TableRow,
  TableCell,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Alert,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import type { PromptSummary, PromptDetailResponse } from '@/types/agent-config';
import { getStatusLabel, getStatusColor } from '@/types/agent-config';
import { getPromptDetail } from '@/api/aiAgents';

export interface PromptDetailExpansionProps {
  /** Prompt summary to display detail for */
  prompt: PromptSummary;
}

/**
 * Highlight {{variable}} placeholders in template text
 */
function highlightTemplateVariables(template: string): JSX.Element {
  const parts = template.split(/(\{\{[^}]+\}\})/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.match(/^\{\{[^}]+\}\}$/)) {
          return (
            <Box
              key={index}
              component="span"
              sx={{
                backgroundColor: 'primary.light',
                color: 'primary.contrastText',
                px: 0.5,
                borderRadius: 0.5,
                fontWeight: 600,
              }}
            >
              {part}
            </Box>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

/**
 * Collapsible section for long content
 */
function ContentSection({
  title,
  content,
  defaultExpanded = false,
  isJson = false,
}: {
  title: string;
  content: string | null | undefined;
  defaultExpanded?: boolean;
  isJson?: boolean;
}): JSX.Element | null {
  if (!content) {
    return (
      <Accordion disabled sx={{ mb: 1 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle2">{title}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
            (Empty)
          </Typography>
        </AccordionSummary>
      </Accordion>
    );
  }

  const isLongContent = content.length > 200;

  return (
    <Accordion defaultExpanded={defaultExpanded || !isLongContent} sx={{ mb: 1 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="subtitle2">{title}</Typography>
        {isLongContent && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
            ({content.length} chars)
          </Typography>
        )}
      </AccordionSummary>
      <AccordionDetails>
        <Box
          sx={{
            backgroundColor: 'grey.50',
            p: 1.5,
            borderRadius: 1,
            maxHeight: 300,
            overflow: 'auto',
          }}
        >
          <Typography
            variant="body2"
            component="pre"
            sx={{
              fontFamily: 'monospace',
              fontSize: '0.75rem',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              m: 0,
            }}
          >
            {isJson ? content : title === 'Template' ? highlightTemplateVariables(content) : content}
          </Typography>
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}

/**
 * Prompt detail expansion panel content.
 * Fetches full prompt detail from API and displays all sections per wireframe.
 */
export function PromptDetailExpansion({ prompt }: PromptDetailExpansionProps): JSX.Element {
  const [detail, setDetail] = useState<PromptDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPromptDetail(prompt.prompt_id, prompt.version);
      setDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompt detail');
    } finally {
      setLoading(false);
    }
  }, [prompt.prompt_id, prompt.version]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  if (loading) {
    return (
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Loading prompt detail...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error" sx={{ mb: 1 }}>
          {error}
        </Alert>
      </Box>
    );
  }

  if (!detail) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="warning">No prompt detail available</Alert>
      </Box>
    );
  }

  // Parse JSON fields for display
  let outputSchema: string | null = null;
  let fewShotExamples: string | null = null;

  if (detail.output_schema_json) {
    try {
      outputSchema = JSON.stringify(JSON.parse(detail.output_schema_json), null, 2);
    } catch {
      outputSchema = detail.output_schema_json;
    }
  }

  if (detail.few_shot_examples_json) {
    try {
      fewShotExamples = JSON.stringify(JSON.parse(detail.few_shot_examples_json), null, 2);
    } catch {
      fewShotExamples = detail.few_shot_examples_json;
    }
  }

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
                  label={getStatusLabel(detail.status)}
                  size="small"
                  color={getStatusColor(detail.status)}
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
                <Typography variant="body2">{detail.author || '—'}</Typography>
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  Changelog
                </Typography>
              </TableCell>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2">
                  {detail.changelog ? `"${detail.changelog}"` : '—'}
                </Typography>
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  Git Commit
                </Typography>
              </TableCell>
              <TableCell sx={{ border: 'none', py: 0.5 }}>
                <Typography variant="body2" fontFamily="monospace">
                  {detail.git_commit || '—'}
                </Typography>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Box>

      {/* System Prompt Section */}
      <ContentSection
        title="System Prompt"
        content={detail.system_prompt}
        defaultExpanded={true}
      />

      {/* Template Section */}
      <ContentSection
        title="Template"
        content={detail.template}
        defaultExpanded={true}
      />

      {/* Output Schema Section */}
      <ContentSection
        title="Output Schema"
        content={outputSchema}
        isJson={true}
      />

      {/* Few-Shot Examples Section */}
      <ContentSection
        title={`Few-Shot Examples${fewShotExamples ? ` (${JSON.parse(detail.few_shot_examples_json || '[]').length})` : ''}`}
        content={fewShotExamples}
        isJson={true}
      />

      {/* A/B Test Configuration */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          A/B Test
        </Typography>
        <Typography variant="body2">
          {detail.ab_test_enabled ? (
            <>
              <Chip label="Enabled" size="small" color="success" sx={{ mr: 1 }} />
              Traffic: {detail.ab_test_traffic_percentage}%
            </>
          ) : (
            <Chip label="Disabled" size="small" color="default" icon={<span>❌</span>} />
          )}
        </Typography>
      </Box>
    </Box>
  );
}
