/**
 * Farmer Import Page
 *
 * CSV bulk import with validation and error reporting.
 * Implements Story 9.5 - Farmer Management (AC 9.5.5).
 *
 * Story 9.5a: collection_point_id removed from required columns.
 * Farmers are assigned to CPs automatically on first delivery.
 *
 * Features:
 * - CSV file upload with drag-and-drop
 * - Validation preview
 * - Error reporting per row
 * - Success/failure summary
 */

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Alert,
  Paper,
  Grid2 as Grid,
  Typography,
  Button,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import DownloadIcon from '@mui/icons-material/Download';
import { PageHeader } from '@fp/ui-components';
import { importFarmers, type FarmerImportResponse, type ImportErrorRow } from '@/api';

// ============================================================================
// Types
// ============================================================================

interface ImportState {
  status: 'idle' | 'uploading' | 'success' | 'error';
  file: File | null;
  result: FarmerImportResponse | null;
  error: string | null;
}

// ============================================================================
// Component
// ============================================================================

export function FarmerImport(): JSX.Element {
  const navigate = useNavigate();

  // State
  const [state, setState] = useState<ImportState>({
    status: 'idle',
    file: null,
    result: null,
    error: null,
  });
  const [dragActive, setDragActive] = useState(false);

  // Handle file selection
  const handleFileSelect = useCallback((file: File) => {
    if (!file.name.endsWith('.csv')) {
      setState((prev) => ({
        ...prev,
        error: 'Please select a CSV file',
        file: null,
      }));
      return;
    }
    setState({
      status: 'idle',
      file,
      result: null,
      error: null,
    });
  }, []);

  // Handle drag events
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  // Handle drop
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelect(e.dataTransfer.files[0]);
      }
    },
    [handleFileSelect]
  );

  // Handle input change
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files[0]) {
        handleFileSelect(e.target.files[0]);
      }
    },
    [handleFileSelect]
  );

  // Handle upload
  const handleUpload = async () => {
    if (!state.file) return;

    setState((prev) => ({ ...prev, status: 'uploading', error: null }));

    try {
      const result = await importFarmers(state.file);
      setState((prev) => ({
        ...prev,
        status: result.error_count > 0 ? 'error' : 'success',
        result,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        status: 'error',
        error: err instanceof Error ? err.message : 'Import failed',
      }));
    }
  };

  // Reset state
  const handleReset = () => {
    setState({
      status: 'idle',
      file: null,
      result: null,
      error: null,
    });
  };

  // Download sample CSV (Story 9.5a: collection_point_id removed)
  const handleDownloadSample = () => {
    const headers = [
      'first_name',
      'last_name',
      'phone',
      'national_id',
      // Story 9.5a: collection_point_id removed - CP assigned on first delivery
      'farm_size_hectares',
      'latitude',
      'longitude',
      'grower_number',
    ];
    const sampleRow = [
      'John',
      'Doe',
      '+254712345678',
      '12345678',
      // Story 9.5a: collection_point_id removed
      '1.5',
      '-1.2345',
      '36.8765',
      'GRW001',
    ];
    const csv = [headers.join(','), sampleRow.join(',')].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'farmer_import_template.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Box>
      <PageHeader
        title="Import Farmers"
        subtitle="Upload a CSV file to bulk import farmers"
        onBack={() => navigate('/farmers')}
      />

      <Grid container spacing={3}>
        {/* Upload Section */}
        <Grid size={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Upload CSV File
            </Typography>

            {state.error && !state.result && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setState((prev) => ({ ...prev, error: null }))}>
                {state.error}
              </Alert>
            )}

            {/* Drop Zone */}
            <Box
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              sx={{
                border: '2px dashed',
                borderColor: dragActive ? 'primary.main' : 'grey.300',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
                cursor: 'pointer',
                bgcolor: dragActive ? 'action.hover' : 'background.paper',
                transition: 'all 0.2s',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                },
              }}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <input
                id="file-input"
                type="file"
                accept=".csv"
                onChange={handleInputChange}
                style={{ display: 'none' }}
              />
              <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                {state.file ? state.file.name : 'Drag and drop your CSV file here'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {state.file
                  ? `${(state.file.size / 1024).toFixed(1)} KB`
                  : 'or click to browse files'}
              </Typography>
            </Box>

            {/* Actions */}
            <Box sx={{ display: 'flex', gap: 2, mt: 3, justifyContent: 'space-between' }}>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleDownloadSample}
              >
                Download Template
              </Button>

              <Box sx={{ display: 'flex', gap: 2 }}>
                {state.file && state.status !== 'uploading' && (
                  <Button variant="outlined" onClick={handleReset}>
                    Clear
                  </Button>
                )}
                <Button
                  variant="contained"
                  startIcon={
                    state.status === 'uploading' ? (
                      <CircularProgress size={20} color="inherit" />
                    ) : (
                      <UploadFileIcon />
                    )
                  }
                  onClick={handleUpload}
                  disabled={!state.file || state.status === 'uploading'}
                >
                  {state.status === 'uploading' ? 'Importing...' : 'Import Farmers'}
                </Button>
              </Box>
            </Box>

            {/* Progress */}
            {state.status === 'uploading' && (
              <Box sx={{ mt: 2 }}>
                <LinearProgress />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Processing CSV file...
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Expected Format */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Expected CSV Format
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              The CSV file should have the following columns (first row as header):
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Column</TableCell>
                    <TableCell>Required</TableCell>
                    <TableCell>Example</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell>first_name</TableCell>
                    <TableCell>
                      <Chip label="Required" size="small" color="error" variant="outlined" />
                    </TableCell>
                    <TableCell>John</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>last_name</TableCell>
                    <TableCell>
                      <Chip label="Required" size="small" color="error" variant="outlined" />
                    </TableCell>
                    <TableCell>Doe</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>phone</TableCell>
                    <TableCell>
                      <Chip label="Required" size="small" color="error" variant="outlined" />
                    </TableCell>
                    <TableCell>+254712345678</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>national_id</TableCell>
                    <TableCell>
                      <Chip label="Required" size="small" color="error" variant="outlined" />
                    </TableCell>
                    <TableCell>12345678</TableCell>
                  </TableRow>
                  {/* Story 9.5a: collection_point_id row removed - CP assigned on first delivery */}
                  <TableRow>
                    <TableCell>farm_size_hectares</TableCell>
                    <TableCell>
                      <Chip label="Required" size="small" color="error" variant="outlined" />
                    </TableCell>
                    <TableCell>1.5</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>latitude</TableCell>
                    <TableCell>
                      <Chip label="Required" size="small" color="error" variant="outlined" />
                    </TableCell>
                    <TableCell>-1.2345</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>longitude</TableCell>
                    <TableCell>
                      <Chip label="Required" size="small" color="error" variant="outlined" />
                    </TableCell>
                    <TableCell>36.8765</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>grower_number</TableCell>
                    <TableCell>
                      <Chip label="Optional" size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>GRW001</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

        {/* Results Section */}
        <Grid size={{ xs: 12, md: 6 }}>
          {state.result && (
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Import Results
              </Typography>

              {/* Summary */}
              <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    flex: 1,
                    textAlign: 'center',
                    bgcolor: state.result.created_count > 0 ? 'success.light' : 'grey.100',
                  }}
                >
                  <CheckCircleIcon
                    sx={{
                      fontSize: 32,
                      color: state.result.created_count > 0 ? 'success.main' : 'grey.400',
                    }}
                  />
                  <Typography variant="h4" fontWeight={600}>
                    {state.result.created_count}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Created
                  </Typography>
                </Paper>

                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    flex: 1,
                    textAlign: 'center',
                    bgcolor: state.result.error_count > 0 ? 'error.light' : 'grey.100',
                  }}
                >
                  <ErrorIcon
                    sx={{
                      fontSize: 32,
                      color: state.result.error_count > 0 ? 'error.main' : 'grey.400',
                    }}
                  />
                  <Typography variant="h4" fontWeight={600}>
                    {state.result.error_count}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Errors
                  </Typography>
                </Paper>
              </Box>

              <Typography variant="body2" color="text.secondary">
                Processed {state.result.total_rows} rows total
              </Typography>

              {/* Success Message */}
              {state.result.error_count === 0 && state.result.created_count > 0 && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  All farmers imported successfully!
                </Alert>
              )}

              {/* Error Details */}
              {state.result.error_count > 0 && state.result.error_rows.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" color="error.main" gutterBottom>
                    Error Details:
                  </Typography>
                  <TableContainer sx={{ maxHeight: 300 }}>
                    <Table size="small" stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell>Row</TableCell>
                          <TableCell>Error</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {state.result.error_rows.map((err: ImportErrorRow, idx: number) => (
                          <TableRow key={idx}>
                            <TableCell>{err.row}</TableCell>
                            <TableCell>
                              <Typography variant="body2" color="error.main">
                                {err.error}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}

              {/* Actions */}
              <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
                <Button variant="outlined" onClick={handleReset}>
                  Import Another File
                </Button>
                <Button variant="contained" onClick={() => navigate('/farmers')}>
                  View Farmers
                </Button>
              </Box>
            </Paper>
          )}

          {!state.result && (
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Notes
              </Typography>
              <Box component="ul" sx={{ pl: 2, color: 'text.secondary' }}>
                <Typography component="li" variant="body2" sx={{ mb: 1 }}>
                  The first row should contain column headers
                </Typography>
                <Typography component="li" variant="body2" sx={{ mb: 1 }}>
                  Phone numbers must be in E.164 format (+254...)
                </Typography>
                {/* Story 9.5a: collection_point_id note removed */}
                <Typography component="li" variant="body2" sx={{ mb: 1 }}>
                  GPS coordinates should be in decimal degrees format
                </Typography>
                <Typography component="li" variant="body2" sx={{ mb: 1 }}>
                  Duplicate phone numbers or national IDs will be rejected
                </Typography>
                <Typography component="li" variant="body2">
                  Collection points are assigned automatically on first delivery
                </Typography>
              </Box>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
