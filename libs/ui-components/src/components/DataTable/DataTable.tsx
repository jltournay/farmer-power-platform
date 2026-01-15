/**
 * DataTable Component
 *
 * Sortable, filterable table with row actions, pagination, and loading states.
 * Wraps MUI DataGrid with Farmer Power styling and simplified API.
 *
 * Accessibility:
 * - Keyboard navigation supported by MUI DataGrid
 * - ARIA table semantics built-in
 * - Focus management for row actions
 */

import {
  DataGrid,
  GridColDef,
  GridRowParams,
  GridActionsCellItem,
  GridPaginationModel,
  GridSortModel,
  GridFilterModel,
  GridRowSelectionModel,
} from '@mui/x-data-grid';
import { Box, Typography, useTheme } from '@mui/material';
import type { ReactNode } from 'react';

/** Row action definition */
export interface DataTableAction<T> {
  /** Unique identifier */
  id: string;
  /** Accessible label */
  label: string;
  /** Action icon */
  icon: ReactNode;
  /** Click handler */
  onClick: (row: T) => void;
  /** Whether action is disabled for this row */
  disabled?: (row: T) => boolean;
  /** Whether to show in menu vs inline */
  showInMenu?: boolean;
}

/** DataTable component props */
export interface DataTableProps<T extends { id: string | number }> {
  /** Column definitions */
  columns: GridColDef[];
  /** Row data */
  rows: T[];
  /** Row actions (shown in actions column) */
  actions?: DataTableAction<T>[];
  /** Loading state */
  loading?: boolean;
  /** Total row count for server-side pagination */
  rowCount?: number;
  /** Pagination model */
  paginationModel?: GridPaginationModel;
  /** Pagination change handler */
  onPaginationChange?: (model: GridPaginationModel) => void;
  /** Sort model */
  sortModel?: GridSortModel;
  /** Sort change handler */
  onSortChange?: (model: GridSortModel) => void;
  /** Filter model */
  filterModel?: GridFilterModel;
  /** Filter change handler */
  onFilterChange?: (model: GridFilterModel) => void;
  /** Row selection model */
  rowSelectionModel?: GridRowSelectionModel;
  /** Row selection change handler */
  onRowSelectionChange?: (model: GridRowSelectionModel) => void;
  /** Row click handler */
  onRowClick?: (row: T) => void;
  /** Whether to enable row selection checkboxes */
  checkboxSelection?: boolean;
  /** Page size options */
  pageSizeOptions?: number[];
  /** Auto height based on row count */
  autoHeight?: boolean;
  /** Custom no rows overlay text */
  noRowsText?: string;
  /** Density */
  density?: 'compact' | 'standard' | 'comfortable';
  /** Height (use when autoHeight is false) */
  height?: number | string;
}

/**
 * DataTable provides a standardized data grid for admin interfaces.
 *
 * @example
 * ```tsx
 * <DataTable
 *   columns={[
 *     { field: 'name', headerName: 'Name', flex: 1 },
 *     { field: 'email', headerName: 'Email', flex: 1 },
 *     { field: 'status', headerName: 'Status', width: 120 },
 *   ]}
 *   rows={farmers}
 *   actions={[
 *     { id: 'edit', label: 'Edit', icon: <EditIcon />, onClick: handleEdit },
 *     { id: 'delete', label: 'Delete', icon: <DeleteIcon />, onClick: handleDelete },
 *   ]}
 *   onRowClick={(row) => navigate(`/farmers/${row.id}`)}
 *   loading={isLoading}
 * />
 * ```
 */
export function DataTable<T extends { id: string | number }>({
  columns,
  rows,
  actions = [],
  loading = false,
  rowCount,
  paginationModel,
  onPaginationChange,
  sortModel,
  onSortChange,
  filterModel,
  onFilterChange,
  rowSelectionModel,
  onRowSelectionChange,
  onRowClick,
  checkboxSelection = false,
  pageSizeOptions = [10, 25, 50],
  autoHeight = true,
  noRowsText = 'No data available',
  density = 'standard',
  height = 400,
}: DataTableProps<T>): JSX.Element {
  const theme = useTheme();

  // Build actions column if actions are provided
  const actionColumn: GridColDef | null =
    actions.length > 0
      ? {
          field: 'actions',
          type: 'actions',
          headerName: 'Actions',
          width: Math.min(actions.length * 40 + 16, 160),
          getActions: (params: GridRowParams<T>) => {
            const row = params.row as T;
            return actions.map((action) => (
              <GridActionsCellItem
                key={action.id}
                icon={action.icon as React.ReactElement}
                label={action.label}
                onClick={() => action.onClick(row)}
                disabled={action.disabled?.(row)}
                showInMenu={action.showInMenu}
                sx={{
                  '&:focus': {
                    outline: `3px solid ${theme.palette.primary.main}`,
                    outlineOffset: '2px',
                  },
                }}
              />
            ));
          },
        }
      : null;

  const allColumns = actionColumn ? [...columns, actionColumn] : columns;

  const handleRowClick = (params: GridRowParams<T>) => {
    onRowClick?.(params.row as T);
  };

  return (
    <Box
      sx={{
        width: '100%',
        height: autoHeight ? 'auto' : height,
        '& .MuiDataGrid-root': {
          border: 'none',
          borderRadius: 2,
          backgroundColor: 'background.paper',
        },
        '& .MuiDataGrid-columnHeaders': {
          backgroundColor: 'grey.50',
          borderBottom: `1px solid ${theme.palette.divider}`,
        },
        '& .MuiDataGrid-row:hover': {
          backgroundColor: 'action.hover',
        },
        '& .MuiDataGrid-row': {
          cursor: onRowClick ? 'pointer' : 'default',
        },
        '& .MuiDataGrid-cell:focus': {
          outline: `3px solid ${theme.palette.primary.main}`,
          outlineOffset: '-3px',
        },
      }}
    >
      <DataGrid
        columns={allColumns}
        rows={rows}
        loading={loading}
        rowCount={rowCount}
        paginationMode={rowCount !== undefined ? 'server' : 'client'}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationChange}
        sortModel={sortModel}
        onSortModelChange={onSortChange}
        filterModel={filterModel}
        onFilterModelChange={onFilterChange}
        rowSelectionModel={rowSelectionModel}
        onRowSelectionModelChange={onRowSelectionChange}
        onRowClick={handleRowClick}
        checkboxSelection={checkboxSelection}
        pageSizeOptions={pageSizeOptions}
        autoHeight={autoHeight}
        density={density}
        disableRowSelectionOnClick={!checkboxSelection}
        slots={{
          noRowsOverlay: () => (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                minHeight: 200,
              }}
            >
              <Typography color="text.secondary">{noRowsText}</Typography>
            </Box>
          ),
        }}
        sx={{
          '& .MuiDataGrid-virtualScroller': {
            minHeight: 200,
          },
        }}
      />
    </Box>
  );
}

export default DataTable;
