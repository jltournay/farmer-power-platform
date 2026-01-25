/**
 * Source Configuration List Page
 *
 * Displays all source configurations with filtering by enabled status and ingestion mode.
 * Implements Story 9.11c - Source Configuration Viewer UI (AC 9.11c.1, AC 9.11c.4).
 */

import { useState, useEffect, useCallback } from 'react';
import { Box, Alert, Chip, CircularProgress, Drawer, Typography, IconButton } from '@mui/material';
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import VisibilityIcon from '@mui/icons-material/Visibility';
import CloseIcon from '@mui/icons-material/Close';
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';
import { listSourceConfigs, getSourceConfig } from '@/api';
import type {
  SourceConfigSummary,
  SourceConfigListResponse,
  SourceConfigDetailResponse,
  IngestionMode,
} from '@/types/source-config';
import {
  getIngestionModeLabel,
  getIngestionModeColor,
  getEnabledLabel,
  getEnabledColor,
} from '@/types/source-config';
import { SourceConfigDetailPanel } from './SourceConfigDetailPanel';

/**
 * Filter definitions for source configuration list.
 */
const SOURCE_CONFIG_FILTER_DEFS: FilterDef[] = [
  {
    id: 'enabled_only',
    label: 'Status',
    options: [
      { value: 'true', label: 'Enabled Only' },
      { value: 'false', label: 'All' },
    ],
  },
  {
    id: 'ingestion_mode',
    label: 'Ingestion Mode',
    options: [
      { value: 'blob_trigger', label: 'Blob Trigger' },
      { value: 'scheduled_pull', label: 'Scheduled Pull' },
    ],
  },
];

/**
 * Source configuration list page component.
 */
export function SourceConfigList(): JSX.Element {
  // State
  const [data, setData] = useState<SourceConfigListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [filters, setFilters] = useState<FilterValues>({});
  const [searchQuery, setSearchQuery] = useState('');

  // Detail panel state
  const [selectedConfig, setSelectedConfig] = useState<SourceConfigDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Data fetching
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await listSourceConfigs({
        page_size: paginationModel.pageSize,
        enabled_only: filters.enabled_only === 'true' ? true : undefined,
        ingestion_mode: (filters.ingestion_mode as IngestionMode | undefined) || undefined,
      });
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load source configurations');
    } finally {
      setLoading(false);
    }
  }, [paginationModel.pageSize, filters.enabled_only, filters.ingestion_mode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Fetch detail when row is selected
  const handleRowSelect = useCallback(async (sourceId: string) => {
    setDetailLoading(true);
    setDetailError(null);
    setDrawerOpen(true);

    try {
      const detail = await getSourceConfig(sourceId);
      setSelectedConfig(detail);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Failed to load source configuration details');
      setSelectedConfig(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleCloseDrawer = () => {
    setDrawerOpen(false);
    setSelectedConfig(null);
    setDetailError(null);
  };

  // Add id field required by DataTable and filter client-side by search query
  type SourceConfigRow = SourceConfigSummary & { id: string };

  const filteredRows: SourceConfigRow[] = (data?.data ?? [])
    .map((config) => ({ ...config, id: config.source_id }))
    .filter((config) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesId = config.source_id.toLowerCase().includes(query);
        const matchesName = config.display_name.toLowerCase().includes(query);
        const matchesDescription = config.description.toLowerCase().includes(query);
        if (!matchesId && !matchesName && !matchesDescription) {
          return false;
        }
      }
      return true;
    });

  // Column definitions
  const columns: GridColDef[] = [
    {
      field: 'source_id',
      headerName: 'Source ID',
      flex: 1,
      minWidth: 160,
    },
    {
      field: 'display_name',
      headerName: 'Display Name',
      flex: 1.5,
      minWidth: 200,
    },
    {
      field: 'ingestion_mode',
      headerName: 'Ingestion Mode',
      width: 140,
      renderCell: (params) => (
        <Chip
          label={getIngestionModeLabel(params.value)}
          size="small"
          color={getIngestionModeColor(params.value)}
          aria-label={`Ingestion mode: ${getIngestionModeLabel(params.value)}`}
        />
      ),
    },
    {
      field: 'enabled',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={getEnabledLabel(params.value)}
          size="small"
          color={getEnabledColor(params.value)}
          aria-label={`Status: ${getEnabledLabel(params.value)}`}
        />
      ),
    },
    {
      field: 'ai_agent_id',
      headerName: 'AI Agent',
      width: 160,
      renderCell: (params) => params.value || '—',
    },
  ];

  // Row actions
  const actions = [
    {
      id: 'view',
      label: 'View',
      icon: <VisibilityIcon fontSize="small" />,
      onClick: (row: SourceConfigRow) => handleRowSelect(row.source_id),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Source Configurations"
        subtitle="Data ingestion pipeline configurations for the platform"
      />

      <FilterBar
        filters={SOURCE_CONFIG_FILTER_DEFS}
        filterValues={filters}
        onFilterChange={(filterId, value) => {
          setFilters((prev) => ({ ...prev, [filterId]: value }));
        }}
        showSearch={true}
        searchTerm={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Search by ID, name, or description..."
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
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
          actions={actions}
          loading={loading}
          rowCount={filteredRows.length}
          paginationModel={paginationModel}
          onPaginationChange={setPaginationModel}
          pageSizeOptions={[10, 25, 50]}
          onRowClick={(row: SourceConfigRow) => handleRowSelect(row.source_id)}
          noRowsText="No source configurations found"
        />
      )}

      {/* Detail Panel Slide-Out Drawer (AC 9.11c.2) */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={handleCloseDrawer}
        PaperProps={{
          sx: { width: { xs: '100%', sm: 600, md: 700 } },
        }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">
            Source Configuration Details
          </Typography>
          <IconButton onClick={handleCloseDrawer} aria-label="Close details">
            <CloseIcon />
          </IconButton>
        </Box>

        {detailLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : detailError ? (
          <Alert severity="error" sx={{ m: 2 }}>
            {detailError}
          </Alert>
        ) : selectedConfig ? (
          <SourceConfigDetailPanel config={selectedConfig} />
        ) : null}
      </Drawer>
    </Box>
  );
}
