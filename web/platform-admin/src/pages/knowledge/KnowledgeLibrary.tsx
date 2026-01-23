/**
 * Knowledge Library Page
 *
 * Displays and manages RAG knowledge documents with filtering, search, and pagination.
 * Story 9.9b: Knowledge Management UI (AC 9.9b.1)
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Alert, Chip, CircularProgress, Typography } from '@mui/material';
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import VisibilityIcon from '@mui/icons-material/Visibility';
import RateReviewIcon from '@mui/icons-material/RateReview';
import EditIcon from '@mui/icons-material/Edit';
import AddIcon from '@mui/icons-material/Add';
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';
import {
  listDocuments,
  searchDocuments,
  type DocumentSummary,
  type DocumentListResponse,
  KNOWLEDGE_DOMAIN_OPTIONS,
  DOCUMENT_STATUS_OPTIONS,
  getDomainLabel,
  getStatusColor,
} from '@/api';

/**
 * Filter definitions for knowledge library.
 */
const FILTER_DEFS: FilterDef[] = [
  {
    id: 'domain',
    label: 'Domain',
    options: KNOWLEDGE_DOMAIN_OPTIONS.map(o => ({ value: o.value, label: o.label })),
  },
  {
    id: 'status',
    label: 'Status',
    options: DOCUMENT_STATUS_OPTIONS.map(o => ({ value: o.value, label: o.label })),
  },
];

type DocumentRow = DocumentSummary & { id: string };

/**
 * Knowledge library page component.
 */
export function KnowledgeLibrary(): JSX.Element {
  const navigate = useNavigate();

  const [data, setData] = useState<DocumentListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 20,
  });
  const [filters, setFilters] = useState<FilterValues>({});
  const [searchQuery, setSearchQuery] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let response: DocumentListResponse;
      if (searchQuery.trim()) {
        response = await searchDocuments({
          query: searchQuery.trim(),
          domain: (filters.domain as string) || undefined,
        });
      } else {
        response = await listDocuments({
          domain: (filters.domain as string) || undefined,
          status: (filters.status as string) || undefined,
          page: paginationModel.page + 1,
          page_size: paginationModel.pageSize,
        });
      }
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [paginationModel.page, paginationModel.pageSize, filters.domain, filters.status, searchQuery]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleFilterChange = (filterId: string, value: string | string[]) => {
    setFilters((prev) => ({ ...prev, [filterId]: value }));
    setPaginationModel((prev) => ({ ...prev, page: 0 }));
  };

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setPaginationModel((prev) => ({ ...prev, page: 0 }));
  };

  const rows: DocumentRow[] = (data?.data ?? []).map((doc) => ({
    ...doc,
    id: doc.document_id,
  }));

  const columns: GridColDef[] = [
    {
      field: 'title',
      headerName: 'Title',
      flex: 2,
      minWidth: 200,
    },
    {
      field: 'version',
      headerName: 'Version',
      width: 90,
      renderCell: (params) => `v${params.value}`,
    },
    {
      field: 'domain',
      headerName: 'Domain',
      width: 150,
      renderCell: (params) => getDomainLabel(params.value),
    },
    {
      field: 'author',
      headerName: 'Author',
      width: 150,
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => (
        <Chip
          label={params.value.charAt(0).toUpperCase() + params.value.slice(1)}
          size="small"
          color={getStatusColor(params.value)}
          aria-label={`Status: ${params.value}`}
        />
      ),
    },
    {
      field: 'updated_at',
      headerName: 'Updated',
      width: 140,
      renderCell: (params) => {
        if (!params.value) return '-';
        return new Date(params.value).toLocaleDateString();
      },
    },
  ];

  const actions = [
    {
      id: 'view',
      label: 'View',
      icon: <VisibilityIcon fontSize="small" />,
      onClick: (row: DocumentRow) => navigate(`/knowledge/${row.document_id}`),
    },
    {
      id: 'review',
      label: 'Review',
      icon: <RateReviewIcon fontSize="small" />,
      onClick: (row: DocumentRow) => navigate(`/knowledge/${row.document_id}/review`),
      show: (row: DocumentRow) => row.status === 'staged',
    },
    {
      id: 'edit',
      label: 'Edit',
      icon: <EditIcon fontSize="small" />,
      onClick: (row: DocumentRow) => navigate(`/knowledge/${row.document_id}`, { state: { edit: true } }),
      show: (row: DocumentRow) => row.status !== 'archived',
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Knowledge Library"
        subtitle="Manage expert knowledge documents for AI recommendations"
        actions={[
          {
            id: 'upload',
            label: 'Upload Document',
            icon: <AddIcon />,
            onClick: () => navigate('/knowledge/upload'),
            variant: 'contained' as const,
          },
        ]}
      />

      <FilterBar
        filters={FILTER_DEFS}
        filterValues={filters}
        onFilterChange={handleFilterChange}
        showSearch={true}
        searchTerm={searchQuery}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search documents..."
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
      ) : rows.length === 0 && !loading ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No documents yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Upload your first knowledge document to power AI recommendations.
          </Typography>
        </Box>
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          actions={actions}
          loading={loading}
          rowCount={data?.pagination?.total_count ?? rows.length}
          paginationModel={paginationModel}
          onPaginationChange={setPaginationModel}
          pageSizeOptions={[10, 20, 50]}
          onRowClick={(row: DocumentRow) => navigate(`/knowledge/${row.document_id}`)}
          noRowsText="No documents match your filters"
        />
      )}
    </Box>
  );
}
