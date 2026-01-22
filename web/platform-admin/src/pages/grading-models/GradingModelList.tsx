/**
 * Grading Model List Page
 *
 * Displays all grading models in the platform with filtering and search.
 * Implements Story 9.6b - Grading Model Management UI (AC 9.6b.1, AC 9.6b.4).
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Alert, Chip, CircularProgress } from '@mui/material';
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';
import {
  listGradingModels,
  type GradingModelListSummary,
  type GradingModelListResponse,
  type GradingType,
  getGradingTypeLabel,
  getGradingTypeColor,
} from '@/api';

/**
 * Filter definitions for grading model list.
 */
const GRADING_TYPE_FILTER_DEFS: FilterDef[] = [
  {
    id: 'grading_type',
    label: 'Grading Type',
    options: [
      { value: 'binary', label: 'Binary' },
      { value: 'ternary', label: 'Ternary' },
      { value: 'multi_level', label: 'Multi-level' },
    ],
  },
];

/**
 * Grading model list page component.
 */
export function GradingModelList(): JSX.Element {
  const navigate = useNavigate();

  // State
  const [data, setData] = useState<GradingModelListResponse | null>(null);
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
      const response = await listGradingModels({
        page_size: paginationModel.pageSize,
        grading_type: (filters.grading_type as GradingType | undefined) || undefined,
      });
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load grading models');
    } finally {
      setLoading(false);
    }
  }, [paginationModel.pageSize, filters.grading_type]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Add id field required by DataTable and filter client-side by search query
  type GradingModelRow = GradingModelListSummary & { id: string };

  const filteredRows: GradingModelRow[] = (data?.data ?? [])
    .map((model) => ({ ...model, id: model.model_id }))
    .filter((model) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesId = model.model_id.toLowerCase().includes(query);
        const matchesCrops = model.crops_name.toLowerCase().includes(query);
        if (!matchesId && !matchesCrops) {
          return false;
        }
      }
      return true;
    });

  // Column definitions
  const columns: GridColDef[] = [
    {
      field: 'model_id',
      headerName: 'Model ID',
      flex: 1,
      minWidth: 160,
    },
    {
      field: 'model_version',
      headerName: 'Version',
      width: 100,
    },
    {
      field: 'crops_name',
      headerName: 'Crops',
      width: 120,
    },
    {
      field: 'market_name',
      headerName: 'Market',
      width: 140,
    },
    {
      field: 'grading_type',
      headerName: 'Grading Type',
      width: 130,
      renderCell: (params) => (
        <Chip
          label={getGradingTypeLabel(params.value)}
          size="small"
          color={getGradingTypeColor(params.value)}
          aria-label={`Grading type: ${getGradingTypeLabel(params.value)}`}
        />
      ),
    },
    {
      field: 'factory_count',
      headerName: 'Factories',
      width: 100,
      type: 'number',
    },
    {
      field: 'attribute_count',
      headerName: 'Attributes',
      width: 100,
      type: 'number',
    },
  ];

  // Row actions
  const actions = [
    {
      id: 'view',
      label: 'View',
      icon: <VisibilityIcon fontSize="small" />,
      onClick: (row: GradingModelRow) => navigate(`/grading-models/${row.model_id}`),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Grading Models"
        subtitle="Quality assessment standards for tea grading"
      />

      <FilterBar
        filters={GRADING_TYPE_FILTER_DEFS}
        filterValues={filters}
        onFilterChange={(filterId, value) => {
          setFilters((prev) => ({ ...prev, [filterId]: value }));
        }}
        showSearch={true}
        searchTerm={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Search by model ID or crops..."
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
          onRowClick={(row: GradingModelRow) => navigate(`/grading-models/${row.model_id}`)}
          noRowsText="No grading models found"
        />
      )}
    </Box>
  );
}
