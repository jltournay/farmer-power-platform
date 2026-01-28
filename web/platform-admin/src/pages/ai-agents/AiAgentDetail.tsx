/**
 * AI Agent Detail Page
 *
 * Full-page detail view for AI agent configuration with all structured sections:
 * Summary, LLM Config, RAG Config, Input/Output Contracts, Linked Prompts, Raw JSON.
 *
 * Implements Story 9.12c - AI Agent & Prompt Viewer UI (AC 9.12c.2, AC 9.12c.6).
 *
 * NOTE: This is a FULL PAGE detail view, NOT a Drawer/slide-out panel.
 * Content density is higher than Source Config, requiring full page layout.
 */

import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Alert,
  Button,
  Chip,
  CircularProgress,
  Typography,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableRow,
  TableCell,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { PageHeader } from '@fp/ui-components';
import { getAiAgent } from '@/api';
import type { AgentConfigDetail, AgentConfig } from '@/types/agent-config';
import {
  getAgentTypeLabel,
  getAgentTypeColor,
  getStatusLabel,
  getStatusColor,
  formatDate,
  parseConfigJson,
  isRagEnabled,
  getRagDomains,
} from '@/types/agent-config';
import { LinkedPromptsTable } from './components/LinkedPromptsTable';

/**
 * Section card wrapper component for consistent styling.
 */
function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" component="h3" gutterBottom sx={{ mb: 2 }}>
          {title}
        </Typography>
        {children}
      </CardContent>
    </Card>
  );
}

/**
 * Detail field row component for consistent key-value display.
 */
function DetailRow({
  label,
  value,
  chip,
  chipColor,
}: {
  label: string;
  value: React.ReactNode;
  chip?: boolean;
  chipColor?: 'info' | 'warning' | 'success' | 'secondary' | 'primary' | 'default';
}): JSX.Element {
  return (
    <TableRow>
      <TableCell
        component="th"
        sx={{
          fontWeight: 500,
          width: '180px',
          borderBottom: 'none',
          py: 1,
          color: 'text.secondary',
        }}
      >
        {label}
      </TableCell>
      <TableCell sx={{ borderBottom: 'none', py: 1 }}>
        {chip && value ? (
          <Chip label={value} size="small" color={chipColor || 'default'} />
        ) : (
          value || '—'
        )}
      </TableCell>
    </TableRow>
  );
}

/**
 * AI Agent Detail Page component.
 */
export function AiAgentDetail(): JSX.Element {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();

  // State
  const [agentDetail, setAgentDetail] = useState<AgentConfigDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rawJsonExpanded, setRawJsonExpanded] = useState(false);

  // Parse config_json
  const configData = useMemo((): AgentConfig | null => {
    if (!agentDetail?.config_json) return null;
    return parseConfigJson(agentDetail.config_json);
  }, [agentDetail?.config_json]);

  // Fetch agent detail
  const fetchDetail = async () => {
    if (!agentId) return;

    setLoading(true);
    setError(null);

    try {
      const detail = await getAiAgent(agentId);
      setAgentDetail(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agent configuration');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  // Handle back navigation
  const handleBack = () => {
    navigate('/ai-agents');
  };

  // Loading state
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  // Error state
  if (error) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={handleBack}
          sx={{ mb: 2 }}
        >
          Back to Agents
        </Button>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={fetchDetail}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      </Box>
    );
  }

  // No data state
  if (!agentDetail) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={handleBack}
          sx={{ mb: 2 }}
        >
          Back to Agents
        </Button>
        <Alert severity="info">Agent configuration not found.</Alert>
      </Box>
    );
  }

  const ragConfig = configData?.rag;
  const llmConfig = configData?.llm;
  const inputContract = configData?.input;
  const outputContract = configData?.output;
  const extractionSchema = configData?.extraction_schema;

  return (
    <Box>
      {/* Back Button */}
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={handleBack}
        sx={{ mb: 2 }}
      >
        Back to Agents
      </Button>

      {/* Page Header */}
      <PageHeader
        title={agentDetail.agent_id}
        subtitle="AI Agent Configuration Detail"
      />

      {/* SUMMARY Section */}
      <SectionCard title="SUMMARY">
        <Table size="small">
          <TableBody>
            <DetailRow label="Agent ID" value={agentDetail.agent_id} />
            <DetailRow label="Version" value={agentDetail.version} />
            <DetailRow
              label="Type"
              value={getAgentTypeLabel(agentDetail.agent_type)}
              chip
              chipColor={getAgentTypeColor(agentDetail.agent_type)}
            />
            <DetailRow
              label="Status"
              value={getStatusLabel(agentDetail.status)}
              chip
              chipColor={getStatusColor(agentDetail.status)}
            />
            <DetailRow label="Description" value={agentDetail.description} />
            <DetailRow label="Updated" value={formatDate(agentDetail.updated_at)} />
            <DetailRow label="Created" value={formatDate(agentDetail.created_at)} />
          </TableBody>
        </Table>
      </SectionCard>

      {/* LLM CONFIGURATION Section */}
      <SectionCard title="LLM CONFIGURATION">
        {llmConfig ? (
          <Table size="small">
            <TableBody>
              <DetailRow label="Model" value={llmConfig.model} />
              <DetailRow label="Temperature" value={llmConfig.temperature?.toString()} />
              <DetailRow label="Max Tokens" value={llmConfig.max_tokens?.toString()} />
              <DetailRow label="Top P" value={llmConfig.top_p?.toString()} />
              <DetailRow label="Response Format" value={llmConfig.response_format} />
              {llmConfig.retry && (
                <>
                  <DetailRow
                    label="Max Retries"
                    value={llmConfig.retry.max_retries?.toString()}
                  />
                  <DetailRow label="Backoff" value={llmConfig.retry.backoff} />
                  <DetailRow
                    label="Timeout"
                    value={
                      llmConfig.retry.timeout_seconds
                        ? `${llmConfig.retry.timeout_seconds}s`
                        : undefined
                    }
                  />
                </>
              )}
            </TableBody>
          </Table>
        ) : (
          <Typography color="text.secondary">No LLM configuration available</Typography>
        )}
      </SectionCard>

      {/* RAG CONFIGURATION Section */}
      <SectionCard title="RAG CONFIGURATION">
        {ragConfig ? (
          <Table size="small">
            <TableBody>
              <DetailRow
                label="RAG Enabled"
                value={isRagEnabled(ragConfig) ? '✅ Yes' : '❌ No'}
              />
              {isRagEnabled(ragConfig) && (
                <>
                  <DetailRow
                    label="Domains"
                    value={getRagDomains(ragConfig).join(', ') || '—'}
                  />
                  <DetailRow label="Top K" value={ragConfig.top_k?.toString()} />
                  <DetailRow
                    label="Score Threshold"
                    value={
                      ragConfig.min_similarity?.toString() ||
                      ragConfig.score_threshold?.toString()
                    }
                  />
                  <DetailRow label="Namespace" value={ragConfig.namespace} />
                  <DetailRow
                    label="Include Metadata"
                    value={ragConfig.include_metadata ? '✅ Yes' : '❌ No'}
                  />
                  <DetailRow
                    label="Reranking"
                    value={ragConfig.rerank_enabled ? '✅ Enabled' : '❌ Disabled'}
                  />
                </>
              )}
            </TableBody>
          </Table>
        ) : (
          <Typography color="text.secondary">Not configured</Typography>
        )}
      </SectionCard>

      {/* INPUT CONTRACT Section */}
      <SectionCard title="INPUT CONTRACT">
        {inputContract || extractionSchema ? (
          <Box>
            {inputContract?.event && (
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>Event:</strong> {inputContract.event}
              </Typography>
            )}
            {extractionSchema?.required_fields && extractionSchema.required_fields.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Required Fields:
                </Typography>
                <Box component="ul" sx={{ pl: 3, m: 0 }}>
                  {extractionSchema.required_fields.map((field) => (
                    <li key={field}>
                      <Typography variant="body2" component="span">
                        <strong>{field}</strong>
                        {extractionSchema.field_types?.[field] && (
                          <Typography
                            component="span"
                            variant="body2"
                            color="text.secondary"
                          >
                            {' '}
                            ({extractionSchema.field_types[field]})
                          </Typography>
                        )}
                      </Typography>
                    </li>
                  ))}
                </Box>
              </Box>
            )}
            {extractionSchema?.optional_fields && extractionSchema.optional_fields.length > 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Optional Fields:
                </Typography>
                <Box component="ul" sx={{ pl: 3, m: 0 }}>
                  {extractionSchema.optional_fields.map((field) => (
                    <li key={field}>
                      <Typography variant="body2" component="span">
                        <strong>{field}</strong>
                        {extractionSchema.field_types?.[field] && (
                          <Typography
                            component="span"
                            variant="body2"
                            color="text.secondary"
                          >
                            {' '}
                            ({extractionSchema.field_types[field]})
                          </Typography>
                        )}
                      </Typography>
                    </li>
                  ))}
                </Box>
              </Box>
            )}
            {inputContract?.schema && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Schema:
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    p: 1.5,
                    bgcolor: 'grey.100',
                    borderRadius: 1,
                    fontSize: '0.8rem',
                    overflow: 'auto',
                    maxHeight: 200,
                  }}
                >
                  {JSON.stringify(inputContract.schema, null, 2)}
                </Box>
              </Box>
            )}
          </Box>
        ) : (
          <Typography color="text.secondary">No input contract defined</Typography>
        )}
      </SectionCard>

      {/* OUTPUT CONTRACT Section */}
      <SectionCard title="OUTPUT CONTRACT">
        {outputContract ? (
          <Box>
            {outputContract.event && (
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>Event:</strong> {outputContract.event}
              </Typography>
            )}
            {outputContract.schema && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Schema:
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    p: 1.5,
                    bgcolor: 'grey.100',
                    borderRadius: 1,
                    fontSize: '0.8rem',
                    overflow: 'auto',
                    maxHeight: 200,
                  }}
                >
                  {JSON.stringify(outputContract.schema, null, 2)}
                </Box>
              </Box>
            )}
          </Box>
        ) : (
          <Typography color="text.secondary">No output contract defined</Typography>
        )}
      </SectionCard>

      {/* LINKED PROMPTS Section (AC 9.12c.3) */}
      <SectionCard title={`LINKED PROMPTS (${agentDetail.prompts?.length || 0})`}>
        {agentDetail.prompts && agentDetail.prompts.length > 0 ? (
          <LinkedPromptsTable prompts={agentDetail.prompts} />
        ) : (
          <Typography color="text.secondary">No prompts linked to this agent</Typography>
        )}
      </SectionCard>

      {/* RAW JSON Section (Collapsible) */}
      <Accordion
        expanded={rawJsonExpanded}
        onChange={(_, expanded) => setRawJsonExpanded(expanded)}
        sx={{ mb: 2 }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>RAW JSON</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box
            component="pre"
            sx={{
              p: 2,
              bgcolor: 'grey.100',
              borderRadius: 1,
              fontSize: '0.75rem',
              fontFamily: 'monospace',
              overflow: 'auto',
              maxHeight: 400,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {configData
              ? JSON.stringify(configData, null, 2)
              : agentDetail.config_json}
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Read-only Warning */}
      <Alert severity="warning" icon={<WarningAmberIcon />} sx={{ mt: 2 }}>
        Read-only view. Use <code>agent-config</code> and <code>prompt-config</code> CLIs to
        modify.
      </Alert>
    </Box>
  );
}
