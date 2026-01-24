/**
 * Knowledge Document Review & Activation Page
 *
 * Two-column layout: document info + content preview (left), Test with AI (right).
 * Approval checkboxes required before activation.
 *
 * Story 9.9b (AC 9.9b.6)
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
  TextField,
  Checkbox,
  FormControlLabel,
  Snackbar,
  Divider,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { PageHeader } from '@fp/ui-components';
import {
  getDocument,
  activateDocument,
  queryKnowledge,
  type DocumentDetail,
  type QueryResultItem,
  getDomainLabel,
  getStatusColor,
} from '@/api';
import { ContentPreview } from './components/ContentPreview';

/**
 * Document review and activation page.
 */
export function KnowledgeReview(): JSX.Element {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Test with AI state
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState<QueryResultItem[]>([]);
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);
  const [testPerformed, setTestPerformed] = useState(false);

  // Approval state
  const [reviewedContent, setReviewedContent] = useState(false);
  const [testedRetrieval, setTestedRetrieval] = useState(false);
  const [approvedForProduction, setApprovedForProduction] = useState(false);

  // Activation state
  const [activating, setActivating] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string }>({ open: false, message: '' });

  const fetchDocument = useCallback(async () => {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    try {
      const doc = await getDocument(documentId);
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

  const handleTestQuery = async () => {
    if (!testQuery.trim() || !document) return;
    setTestLoading(true);
    setTestError(null);
    try {
      const response = await queryKnowledge({
        query: testQuery.trim(),
        domains: [document.domain as 'plant_diseases' | 'tea_cultivation' | 'weather_patterns' | 'quality_standards' | 'regional_context'],
        top_k: 3,
        namespace: document.pinecone_namespace || undefined,
      });
      setTestResults(response.matches);
      setTestPerformed(true);
    } catch (err) {
      setTestError(err instanceof Error ? err.message : 'Query failed');
    } finally {
      setTestLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!documentId) return;
    setActivating(true);
    try {
      await activateDocument(documentId);
      setSnackbar({ open: true, message: 'Document activated for production' });
      setTimeout(() => navigate(`/knowledge/${documentId}`), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate document');
    } finally {
      setActivating(false);
    }
  };

  const allApproved = reviewedContent && testedRetrieval && approvedForProduction;

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
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/knowledge')}>
          Back to Library
        </Button>
        <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
      </Box>
    );
  }

  if (!document) return <></>;

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/knowledge')} sx={{ mb: 2 }}>
        Back to Library
      </Button>

      <PageHeader
        title="Review Document"
        subtitle={document.title}
      />

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <Chip
          label={document.status.charAt(0).toUpperCase() + document.status.slice(1)}
          color={getStatusColor(document.status)}
        />
        <Typography variant="body2" color="text.secondary">
          v{document.version} - {getDomainLabel(document.domain)}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Two-column layout */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
        {/* Left column: Document info + content preview */}
        <Box>
          <Typography variant="subtitle1" gutterBottom>Document Info</Typography>
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography variant="body2"><strong>Domain:</strong> {getDomainLabel(document.domain)}</Typography>
            <Typography variant="body2"><strong>Author:</strong> {document.metadata?.author || '-'}</Typography>
            <Typography variant="body2"><strong>Version:</strong> {document.version}</Typography>
            <Typography variant="body2">
              <strong>Created:</strong> {document.created_at ? new Date(document.created_at).toLocaleDateString() : '-'}
            </Typography>
          </Paper>

          <Typography variant="subtitle1" gutterBottom>Content Preview</Typography>
          <ContentPreview content={document.content} maxHeight={400} />
        </Box>

        {/* Right column: Test with AI */}
        <Box>
          <Typography variant="subtitle1" gutterBottom>Test with AI</Typography>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Ask a test question to verify the document is retrievable by AI agents.
            </Typography>

            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Ask a test question..."
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleTestQuery(); }}
              />
              <Button
                variant="contained"
                onClick={handleTestQuery}
                disabled={!testQuery.trim() || testLoading}
                sx={{ whiteSpace: 'nowrap' }}
              >
                {testLoading ? 'Testing...' : 'Test'}
              </Button>
            </Box>

            {testError && (
              <Alert severity="error" sx={{ mb: 2 }}>{testError}</Alert>
            )}

            {testPerformed && testResults.length > 0 && (
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <CheckCircleIcon fontSize="small" color="success" />
                  <Typography variant="body2">Document content retrieved successfully</Typography>
                </Box>
                {testResults.map((result, idx) => (
                  <Paper key={result.chunk_id || idx} variant="outlined" sx={{ p: 1.5, mb: 1, bgcolor: 'grey.50' }}>
                    <Typography variant="caption" color="text.secondary">
                      Score: {(result.score * 100).toFixed(0)}% - {result.title}
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 0.5, fontSize: '0.8rem' }}>
                      {result.content.slice(0, 200)}{result.content.length > 200 ? '...' : ''}
                    </Typography>
                  </Paper>
                ))}
              </Box>
            )}

            {testPerformed && testResults.length === 0 && !testError && (
              <Alert severity="info">
                No matching content found. The document may need to be vectorized first.
              </Alert>
            )}
          </Paper>
        </Box>
      </Box>

      {/* Approval section */}
      <Divider sx={{ my: 3 }} />
      <Typography variant="h6" gutterBottom>Approval</Typography>
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <FormControlLabel
          control={<Checkbox checked={reviewedContent} onChange={(e) => setReviewedContent(e.target.checked)} />}
          label="I have reviewed the content for accuracy"
        />
        <FormControlLabel
          control={<Checkbox checked={testedRetrieval} onChange={(e) => setTestedRetrieval(e.target.checked)} />}
          label="I have tested AI retrieval with sample questions"
        />
        <FormControlLabel
          control={<Checkbox checked={approvedForProduction} onChange={(e) => setApprovedForProduction(e.target.checked)} />}
          label="I approve this document for production use"
        />
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button onClick={() => navigate('/knowledge')}>Back to Library</Button>
          <Button onClick={() => navigate(`/knowledge/${documentId}`)}>Edit</Button>
        </Box>
        <Button
          variant="contained"
          color="success"
          onClick={handleActivate}
          disabled={!allApproved || activating}
        >
          {activating ? 'Activating...' : 'Activate for Production'}
        </Button>
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
}
