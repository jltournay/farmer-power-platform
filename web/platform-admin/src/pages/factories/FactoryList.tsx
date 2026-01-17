/**
 * Factory List Page
 *
 * Displays all factories in the platform with CRUD operations.
 * Implements Story 9.3 - Factory Management (AC1).
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Alert, Chip, CircularProgress } from '@mui/material';
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import AddIcon from '@mui/icons-material/Add';
import VisibilityIcon from '@mui/icons-material/Visibility';
import EditIcon from '@mui/icons-material/Edit';
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';
import { listFactories, listRegions, type FactorySummary, type FactoryListResponse, type RegionSummary } from '@/api';

/**
 * Filter definitions for factory list.
 */
function getFilterDefs(regions: RegionSummary[]): FilterDef[] {
  return [
    {
      id: 'region_id',
      label: 'Region',
      options: regions.map((r) => ({ value: r.id, label: r.name })),
    },
    {
      id: 'active_only',
      label: 'Status',
      options: [
        { value: 'true', label: 'Active Only' },
        { value: 'false', label: 'All Factories' },
      ],
    },
  ];
}

/**
 * Factory list page component.
 */
export function FactoryList(): JSX.Element {
  const navigate = useNavigate();

  // State
  const [data, setData] = useState<FactoryListResponse | null>(null);
  const [regions, setRegions] = useState<RegionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [filters, setFilters] = useState<FilterValues>({});
  const [searchQuery, setSearchQuery] = useState('');

  // Region lookup map for display
  const regionMap = regions.reduce<Record<string, string>>((acc, r) => {
    acc[r.id] = r.name;
    return acc;
  }, {});

  // Fetch regions for filter dropdown
  const fetchRegions = useCallback(async () => {
    try {
      const response = await listRegions({ page_size: 100, active_only: true });
      setRegions(response.data);
    } catch {
      // Silently fail - regions filter will just be empty
      console.warn('Failed to load regions for filter');
    }
  }, []);

  // Data fetching
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await listFactories({
        page_size: paginationModel.pageSize,
        region_id: filters.region_id as string | undefined,
        active_only: filters.active_only === 'true',
      });
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load factories');
    } finally {
      setLoading(false);
    }
  }, [paginationModel.pageSize, filters.region_id, filters.active_only]);

  useEffect(() => {
    fetchRegions();
  }, [fetchRegions]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Filter client-side by search query (name or code)
  const filteredRows = data?.data.filter((factory) => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesName = factory.name.toLowerCase().includes(query);
      const matchesCode = factory.code.toLowerCase().includes(query);
      if (!matchesName && !matchesCode) {
        return false;
      }
    }
    return true;
  }) ?? [];

  // Column definitions
  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Factory Name',
      flex: 1,
      minWidth: 180,
    },
    {
      field: 'code',
      headerName: 'Code',
      width: 120,
    },
    {
      field: 'region_id',
      headerName: 'Region',
      flex: 1,
      minWidth: 150,
      valueGetter: (value: string) => regionMap[value] ?? value,
    },
    {
      field: 'collection_point_count',
      headerName: 'CPs',
      width: 80,
      type: 'number',
    },
    {
      field: 'farmer_count',
      headerName: 'Farmers',
      width: 100,
      type: 'number',
    },
    {
      field: 'is_active',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Active' : 'Inactive'}
          size="small"
          color={params.value ? 'success' : 'default'}
          variant={params.value ? 'filled' : 'outlined'}
        />
      ),
    },
  ];

  // Row actions
  const actions = [
    {
      id: 'view',
      label: 'View',
      icon: <VisibilityIcon fontSize="small" />,
      onClick: (row: FactorySummary) => navigate(`/factories/${row.id}`),
    },
    {
      id: 'edit',
      label: 'Edit',
      icon: <EditIcon fontSize="small" />,
      onClick: (row: FactorySummary) => navigate(`/factories/${row.id}/edit`),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Factories"
        subtitle="Manage tea processing facilities and their configuration"
        actions={[
          {
            id: 'create',
            label: 'Add Factory',
            icon: <AddIcon />,
            variant: 'contained',
            onClick: () => navigate('/factories/new'),
          },
        ]}
      />

      <FilterBar
        filters={getFilterDefs(regions)}
        filterValues={filters}
        onFilterChange={(filterId, value) => {
          setFilters((prev) => ({ ...prev, [filterId]: value }));
        }}
        showSearch={true}
        searchTerm={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Search by name or code..."
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
          onRowClick={(row) => navigate(`/factories/${row.id}`)}
          noRowsText="No factories found"
        />
      )}
    </Box>
  );
}
