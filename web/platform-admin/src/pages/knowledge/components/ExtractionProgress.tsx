/**
 * Extraction Progress Component
 *
 * Displays real-time extraction progress via SSE with progress bar and status messages.
 * Story 9.9b (AC 9.9b.3)
 */

import { useEffect, useRef, useState } from 'react';
import { Box, LinearProgress, Typography, Alert } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { createExtractionProgressStream, type ExtractionProgressEvent } from '@/api';

interface ExtractionProgressProps {
  documentId: string;
  jobId: string;
  onComplete: () => void;
  onError: (error: string) => void;
}

/**
 * Shows real-time extraction progress via SSE events.
 */
export function ExtractionProgress({ documentId, jobId, onComplete, onError }: ExtractionProgressProps): JSX.Element {
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Starting extraction...');
  const [method, setMethod] = useState<string | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const cleanup = createExtractionProgressStream(
      documentId,
      jobId,
      (event: ExtractionProgressEvent) => {
        setProgress(event.percent);
        setStatusMessage(event.message || `Pages ${event.pages_processed}/${event.total_pages}`);
        if (event.status && !method) {
          setMethod(event.status);
        }
        setConnectionError(null);
      },
      () => {
        setProgress(100);
        setStatusMessage('Extraction complete');
        onComplete();
      },
      (error: string) => {
        setConnectionError(error);
        onError(error);
      },
    );

    cleanupRef.current = cleanup;

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
    };
  }, [documentId, jobId, onComplete, onError, method]);

  return (
    <Box sx={{ py: 3 }}>
      {connectionError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {connectionError}
        </Alert>
      )}

      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {progress < 100 ? 'Analyzing document...' : 'Complete'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {progress}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={progress}
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Extraction progress"
          sx={{ height: 8, borderRadius: 4 }}
        />
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {method && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckCircleIcon fontSize="small" color="success" />
            <Typography variant="body2">Detected: {method}</Typography>
          </Box>
        )}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {progress >= 100 ? (
            <CheckCircleIcon fontSize="small" color="success" />
          ) : (
            <Box sx={{ width: 20, height: 20 }} />
          )}
          <Typography variant="body2">{statusMessage}</Typography>
        </Box>
      </Box>
    </Box>
  );
}
