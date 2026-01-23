/**
 * Version History Component
 *
 * Displays version history list with dates, authors, and change summaries.
 * Story 9.9b (AC 9.9b.7)
 */

import { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Paper, Button, Chip, CircularProgress, Alert } from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import RestoreIcon from '@mui/icons-material/Restore';
import { listDocuments, type DocumentSummary } from '@/api';

interface VersionHistoryProps {
  documentId: string;
  currentVersion: number;
  onViewVersion: (version: number) => void;
  onRollback: (version: number) => void;
}

/**
 * Renders version history for a document.
 */
export function VersionHistory({ documentId, currentVersion, onViewVersion, onRollback }: VersionHistoryProps): JSX.Element {
  const [versions, setVersions] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVersions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // List all documents and filter by document_id to get all versions
      const response = await listDocuments({ page_size: 100 });
      const docVersions = response.data
        .filter(d => d.document_id === documentId)
        .sort((a, b) => b.version - a.version);
      setVersions(docVersions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load versions');
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (versions.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No version history available
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {versions.map((ver) => (
        <Paper key={`${ver.document_id}-v${ver.version}`} variant="outlined" sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Typography variant="subtitle2">
                  v{ver.version}
                </Typography>
                {ver.version === currentVersion && (
                  <Chip label="Current" size="small" color="primary" />
                )}
                <Chip
                  label={ver.status.charAt(0).toUpperCase() + ver.status.slice(1)}
                  size="small"
                  variant="outlined"
                />
              </Box>
              <Typography variant="body2" color="text.secondary">
                {ver.author || 'Unknown author'}
                {ver.updated_at && ` - ${new Date(ver.updated_at).toLocaleDateString()}`}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                size="small"
                startIcon={<VisibilityIcon />}
                onClick={() => onViewVersion(ver.version)}
              >
                View
              </Button>
              {ver.version !== currentVersion && ver.status !== 'active' && (
                <Button
                  size="small"
                  startIcon={<RestoreIcon />}
                  onClick={() => onRollback(ver.version)}
                >
                  Rollback
                </Button>
              )}
            </Box>
          </Box>
        </Paper>
      ))}
    </Box>
  );
}
