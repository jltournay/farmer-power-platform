/**
 * AI Agent List Page
 *
 * Displays all AI agent configurations with filtering by agent type and status.
 * Implements Story 9.12c - AI Agent & Prompt Viewer UI (AC 9.12c.1, AC 9.12c.5, AC 9.12c.6).
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Alert, Button, Chip, CircularProgress } from '@mui/material';
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';
import { listAiAgents } from '@/api';
import type {
  AgentConfigSummary,
  AgentConfigListResponse,
  AgentType,
  AgentStatus,
} from '@/types/agent-config';
import {
  getAgentTypeLabel,
  getAgentTypeColor,
  getStatusLabel,
  getStatusColor,
  formatDate,
} from '@/types/agent-config';

/**
 * Filter definitions for AI agent list.
 */
const AI_AGENT_FILTER_DEFS: FilterDef[] = [
  {
    id: 'agent_type',
    label: 'Agent Type',
    options: [
      { value: 'extractor', label: 'Extractor' },
      { value: 'explorer', label: 'Explorer' },
      { value: 'generator', label: 'Generator' },
      { value: 'conversational', label: 'Conversational' },
      { value: 'tiered-vision', label: 'Tiered Vision' },
    ],
  },
  {
    id: 'status',
    label: 'Status',
    options: [
      { value: 'active', label: 'Active' },
      { value: 'staged', label: 'Staged' },
      { value: 'archived', label: 'Archived' },
      { value: 'draft', label: 'Draft' },
    ],
  },
];

/**
 * AI agent list page component.
 */
export function AiAgentList(): JSX.Element {
  const navigate = useNavigate();

  // State
  const [data, setData] = useState<AgentConfigListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [filters, setFilters] = useState<FilterValues>({});
  const [searchQuery, setSearchQuery] = useState('');

  // Data fetching
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await listAiAgents({
        page_size: paginationModel.pageSize,
        agent_type: (filters.agent_type as AgentType | undefined) || undefined,
        status: (filters.status as AgentStatus | undefined) || undefined,
      });
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load AI agent configurations');
    } finally {
      setLoading(false);
    }
  }, [paginationModel.pageSize, filters.agent_type, filters.status]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Navigate to detail page when row is clicked
  const handleRowClick = useCallback(
    (agentId: string) => {
      navigate(`/ai-agents/${encodeURIComponent(agentId)}`);
    },
    [navigate]
  );

  // Add id field required by DataTable and filter client-side by search query
  type AgentConfigRow = AgentConfigSummary & { id: string };

  const filteredRows: AgentConfigRow[] = (data?.data ?? [])
    .map((config) => ({ ...config, id: config.agent_id }))
    .filter((config) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesId = config.agent_id.toLowerCase().includes(query);
        const matchesDescription = config.description.toLowerCase().includes(query);
        const matchesModel = config.model.toLowerCase().includes(query);
        if (!matchesId && !matchesDescription && !matchesModel) {
          return false;
        }
      }
      return true;
    });

  // Column definitions
  const columns: GridColDef[] = [
    {
      field: 'agent_id',
      headerName: 'Agent ID',
      flex: 1,
      minWidth: 180,
    },
    {
      field: 'agent_type',
      headerName: 'Type',
      width: 130,
      renderCell: (params) => (
        <Chip
          label={getAgentTypeLabel(params.value)}
          size="small"
          color={getAgentTypeColor(params.value)}
          aria-label={`Agent type: ${getAgentTypeLabel(params.value)}`}
        />
      ),
    },
    {
      field: 'version',
      headerName: 'Version',
      width: 100,
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={getStatusLabel(params.value)}
          size="small"
          color={getStatusColor(params.value)}
          aria-label={`Status: ${getStatusLabel(params.value)}`}
        />
      ),
    },
    {
      field: 'model',
      headerName: 'Model',
      width: 180,
      renderCell: (params) => params.value || '—',
    },
    {
      field: 'prompt_count',
      headerName: 'Prompts',
      width: 90,
      align: 'center',
      headerAlign: 'center',
    },
    {
      field: 'updated_at',
      headerName: 'Updated',
      width: 150,
      renderCell: (params) => formatDate(params.value),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="AI Agents"
        subtitle="AI agent configurations and linked prompts"
      />

      <FilterBar
        filters={AI_AGENT_FILTER_DEFS}
        filterValues={filters}
        onFilterChange={(filterId, value) => {
          setFilters((prev) => ({ ...prev, [filterId]: value }));
        }}
        showSearch={true}
        searchTerm={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Search by agent ID, description, or model..."
      />

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={fetchData}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {loading && !data ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <DataTable
          columns={columns}
          rows={filteredRows}
          loading={loading}
          rowCount={filteredRows.length}
          paginationModel={paginationModel}
          onPaginationChange={setPaginationModel}
          pageSizeOptions={[10, 25, 50]}
          onRowClick={(row: AgentConfigRow) => handleRowClick(row.agent_id)}
          noRowsText="No AI agents found"
        />
      )}
    </Box>
  );
}
