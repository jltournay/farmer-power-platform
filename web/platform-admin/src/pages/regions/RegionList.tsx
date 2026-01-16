/**
 * Region List Page
 *
 * Displays all regions in the platform with CRUD operations.
 * Implements Story 9.2 - Region Management.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Alert, Chip, CircularProgress } from '@mui/material';
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import AddIcon from '@mui/icons-material/Add';
import VisibilityIcon from '@mui/icons-material/Visibility';
import EditIcon from '@mui/icons-material/Edit';
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';
import { listRegions, type RegionSummary, type RegionListResponse } from '@/api';

/**
 * Altitude band display colors.
 */
const ALTITUDE_BAND_COLORS: Record<string, 'success' | 'warning' | 'info'> = {
  highland: 'success',
  midland: 'warning',
  lowland: 'info',
};

/**
 * Filter definitions for region list.
 */
const FILTER_DEFS: FilterDef[] = [
  {
    id: 'altitude_band',
    label: 'Altitude Band',
    options: [
      { value: 'highland', label: 'Highland' },
      { value: 'midland', label: 'Midland' },
      { value: 'lowland', label: 'Lowland' },
    ],
  },
  {
    id: 'active_only',
    label: 'Status',
    options: [
      { value: 'true', label: 'Active Only' },
      { value: 'false', label: 'All Regions' },
    ],
  },
];

/**
 * Region list page component.
 */
export function RegionList(): JSX.Element {
  const navigate = useNavigate();

  // State
  const [data, setData] = useState<RegionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [filters, setFilters] = useState<FilterValues>({});

  // Data fetching
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await listRegions({
        page_size: paginationModel.pageSize,
        active_only: filters.active_only === 'true',
      });
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load regions');
    } finally {
      setLoading(false);
    }
  }, [paginationModel.pageSize, filters.active_only]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Filter client-side by altitude band
  const filteredRows = data?.data.filter((region) => {
    if (filters.altitude_band && region.altitude_band !== filters.altitude_band) {
      return false;
    }
    return true;
  }) ?? [];

  // Column definitions
  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Region Name',
      flex: 1,
      minWidth: 180,
    },
    {
      field: 'county',
      headerName: 'County',
      flex: 1,
      minWidth: 140,
    },
    {
      field: 'country',
      headerName: 'Country',
      width: 100,
    },
    {
      field: 'altitude_band',
      headerName: 'Altitude',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={ALTITUDE_BAND_COLORS[params.value as string] ?? 'default'}
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
      onClick: (row: RegionSummary) => navigate(`/regions/${row.id}`),
    },
    {
      id: 'edit',
      label: 'Edit',
      icon: <EditIcon fontSize="small" />,
      onClick: (row: RegionSummary) => navigate(`/regions/${row.id}/edit`),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Regions"
        subtitle="Manage geographic regions and their configuration"
        actions={[
          {
            id: 'create',
            label: 'Add Region',
            icon: <AddIcon />,
            variant: 'contained',
            onClick: () => navigate('/regions/new'),
          },
        ]}
      />

      <FilterBar
        filters={FILTER_DEFS}
        filterValues={filters}
        onFilterChange={(filterId, value) => {
          setFilters((prev) => ({ ...prev, [filterId]: value }));
        }}
        showSearch={false}
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
          onRowClick={(row) => navigate(`/regions/${row.id}`)}
          noRowsText="No regions found"
        />
      )}
    </Box>
  );
}
