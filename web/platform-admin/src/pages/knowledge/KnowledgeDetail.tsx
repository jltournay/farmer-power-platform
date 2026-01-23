/**
 * Knowledge Document Detail Page
 *
 * Displays document info, content preview, and version history.
 * Provides lifecycle actions (stage, activate, archive, edit).
 *
 * Story 9.9b (AC 9.9b.6, AC 9.9b.7)
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import PublishIcon from '@mui/icons-material/Publish';
import ArchiveIcon from '@mui/icons-material/Archive';
import RateReviewIcon from '@mui/icons-material/RateReview';
import DeleteIcon from '@mui/icons-material/Delete';
import RestoreIcon from '@mui/icons-material/Restore';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { PageHeader } from '@fp/ui-components';
import {
  getDocument,
  updateDocument,
  stageDocument,
  archiveDocument,
  deleteDocument,
  rollbackDocument,
  type DocumentDetail as DocumentDetailType,
  getDomainLabel,
  getStatusColor,
} from '@/api';
import { ContentPreview } from './components/ContentPreview';
import { VersionHistory } from './components/VersionHistory';

/**
 * Document detail page component.
 */
export function KnowledgeDetail(): JSX.Element {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<DocumentDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string }>({ open: false, message: '' });
  const [actionLoading, setActionLoading] = useState(false);

  // Edit dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [changeSummary, setChangeSummary] = useState('');

  const fetchDocument = useCallback(async (version?: number) => {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    try {
      const doc = await getDocument(documentId, version);
      setDocument(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    fetchDocument();
  }, [fetchDocument]);

  const handleStage = async () => {
    if (!documentId) return;
    setActionLoading(true);
    try {
      const updated = await stageDocument(documentId);
      setDocument(updated);
      setSnackbar({ open: true, message: 'Document staged for review' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stage document');
    } finally {
      setActionLoading(false);
    }
  };

  const handleArchive = async () => {
    if (!documentId) return;
    setActionLoading(true);
    try {
      const updated = await archiveDocument(documentId);
      setDocument(updated);
      setSnackbar({ open: true, message: 'Document archived' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive document');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!documentId) return;
    setActionLoading(true);
    try {
      await deleteDocument(documentId);
      setSnackbar({ open: true, message: 'Document deleted (archived)' });
      setTimeout(() => navigate('/knowledge'), 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    } finally {
      setActionLoading(false);
    }
  };

  const handleEditOpen = () => {
    if (!document) return;
    setEditTitle(document.title);
    setEditContent(document.content);
    setChangeSummary('');
    setEditDialogOpen(true);
  };

  const handleEditSave = async () => {
    if (!documentId || !changeSummary.trim()) return;
    setActionLoading(true);
    try {
      const updated = await updateDocument(documentId, {
        title: editTitle !== document?.title ? editTitle : undefined,
        content: editContent !== document?.content ? editContent : undefined,
        change_summary: changeSummary,
      });
      setDocument(updated);
      setEditDialogOpen(false);
      setSnackbar({ open: true, message: 'New version created' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update document');
    } finally {
      setActionLoading(false);
    }
  };

  const handleViewVersion = (version: number) => {
    fetchDocument(version);
  };

  const handleRollback = async (targetVersion: number) => {
    if (!documentId) return;
    setActionLoading(true);
    try {
      const updated = await rollbackDocument(documentId, targetVersion);
      setDocument(updated);
      setSnackbar({ open: true, message: `Rolled back to v${targetVersion} (new draft created)` });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && !document) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/knowledge')} sx={{ mb: 2 }}>
          Back to Library
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!document) return <></>;

  const status = document.status;

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/knowledge')} sx={{ mb: 2 }}>
        Back to Library
      </Button>

      <PageHeader
        title={document.title}
        subtitle={`v${document.version} - ${getDomainLabel(document.domain)}`}
        actions={getActions(status)}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Chip
          label={status.charAt(0).toUpperCase() + status.slice(1)}
          color={getStatusColor(status)}
        />
        <Chip label={getDomainLabel(document.domain)} variant="outlined" />
        {document.metadata?.author && (
          <Chip label={`Author: ${document.metadata.author}`} variant="outlined" size="small" />
        )}
        {document.source_file && (
          <Chip
            label={`Confidence: ${Math.round(document.source_file.extraction_confidence * 100)}%`}
            variant="outlined"
            size="small"
          />
        )}
      </Box>

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 1 }}>
          <Typography variant="body2"><strong>Document ID:</strong> {document.document_id}</Typography>
          <Typography variant="body2"><strong>Version:</strong> {document.version}</Typography>
          <Typography variant="body2"><strong>Author:</strong> {document.metadata?.author || '-'}</Typography>
          <Typography variant="body2"><strong>Source:</strong> {document.metadata?.source || '-'}</Typography>
          <Typography variant="body2"><strong>Region:</strong> {document.metadata?.region || '-'}</Typography>
          <Typography variant="body2">
            <strong>Created:</strong> {document.created_at ? new Date(document.created_at).toLocaleString() : '-'}
          </Typography>
          <Typography variant="body2">
            <strong>Updated:</strong> {document.updated_at ? new Date(document.updated_at).toLocaleString() : '-'}
          </Typography>
          {document.change_summary && (
            <Typography variant="body2"><strong>Change:</strong> {document.change_summary}</Typography>
          )}
        </Box>
      </Paper>

      <Typography variant="h6" gutterBottom>Content</Typography>
      <ContentPreview content={document.content} maxHeight={500} />

      <Typography variant="h6" sx={{ mt: 4, mb: 2 }}>Version History</Typography>
      <VersionHistory
        documentId={document.document_id}
        currentVersion={document.version}
        onViewVersion={handleViewVersion}
        onRollback={handleRollback}
      />

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Document</DialogTitle>
        <DialogContent>
          <TextField
            label="Title"
            fullWidth
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            sx={{ mt: 1, mb: 2 }}
          />
          <TextField
            label="Content"
            multiline
            rows={12}
            fullWidth
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            label="Change Summary (required)"
            fullWidth
            required
            value={changeSummary}
            onChange={(e) => setChangeSummary(e.target.value)}
            helperText="Describe what changed in this version"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleEditSave}
            disabled={!changeSummary.trim() || actionLoading}
          >
            Save New Version
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );

  function getActions(docStatus: string) {
    const actions: { id: string; label: string; icon: JSX.Element; onClick: () => void; variant?: 'text' | 'outlined' | 'contained'; disabled?: boolean }[] = [];

    if (docStatus === 'draft') {
      actions.push(
        { id: 'edit', label: 'Edit', icon: <EditIcon />, onClick: handleEditOpen },
        { id: 'stage', label: 'Stage', icon: <PublishIcon />, onClick: handleStage, variant: 'contained' },
        { id: 'delete', label: 'Delete', icon: <DeleteIcon />, onClick: handleDelete },
      );
    } else if (docStatus === 'staged') {
      actions.push(
        { id: 'review', label: 'Review & Activate', icon: <RateReviewIcon />, onClick: () => navigate(`/knowledge/${documentId}/review`), variant: 'contained' },
        { id: 'edit', label: 'Edit', icon: <EditIcon />, onClick: handleEditOpen },
        { id: 'archive', label: 'Archive', icon: <ArchiveIcon />, onClick: handleArchive },
      );
    } else if (docStatus === 'active') {
      actions.push(
        { id: 'edit', label: 'Edit', icon: <EditIcon />, onClick: handleEditOpen },
        { id: 'archive', label: 'Archive', icon: <ArchiveIcon />, onClick: handleArchive },
      );
    } else if (docStatus === 'archived') {
      actions.push(
        { id: 'rollback', label: 'Restore as Draft', icon: <RestoreIcon />, onClick: () => handleRollback(document!.version) },
      );
    }

    return actions.map(a => ({ ...a, disabled: actionLoading }));
  }
}
