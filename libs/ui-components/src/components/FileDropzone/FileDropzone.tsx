/**
 * FileDropzone Component
 *
 * Drag-and-drop file upload with progress and validation.
 * Used for document uploads in admin interfaces.
 *
 * Accessibility:
 * - Keyboard accessible file input
 * - ARIA labels for screen readers
 * - Progress announcements
 * - Error messages linked to input
 */

import { useState, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  IconButton,
  LinearProgress,
  Button,
  useTheme,
  Alert,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

/** Uploaded file info */
export interface UploadedFile {
  /** File name */
  name: string;
  /** File size in bytes */
  size: number;
  /** MIME type */
  type: string;
  /** Upload progress (0-100) */
  progress?: number;
  /** Upload error message */
  error?: string;
  /** Whether upload is complete */
  complete?: boolean;
  /** Original File object */
  file?: File;
}

/** FileDropzone component props */
export interface FileDropzoneProps {
  /** Accepted file types (e.g., '.pdf,.doc,.docx') */
  accept?: string;
  /** Maximum file size in bytes */
  maxSize?: number;
  /** Whether multiple files are allowed */
  multiple?: boolean;
  /** Currently uploaded/uploading files */
  files?: UploadedFile[];
  /** File selection handler */
  onFilesSelected?: (files: File[]) => void;
  /** File removal handler */
  onFileRemove?: (index: number) => void;
  /** Upload handler - should update progress */
  onUpload?: (file: File) => Promise<void>;
  /** Whether upload is disabled */
  disabled?: boolean;
  /** Helper text */
  helperText?: string;
  /** Error message */
  error?: string;
}

/**
 * Format file size for display.
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * FileDropzone provides drag-and-drop file upload functionality.
 *
 * @example
 * ```tsx
 * <FileDropzone
 *   accept=".pdf,.doc,.docx"
 *   maxSize={10 * 1024 * 1024} // 10MB
 *   files={uploadedFiles}
 *   onFilesSelected={handleFilesSelected}
 *   onFileRemove={handleRemove}
 *   helperText="Supported formats: PDF, Word. Max size: 10MB"
 * />
 * ```
 */
export function FileDropzone({
  accept,
  maxSize,
  multiple = false,
  files = [],
  onFilesSelected,
  onFileRemove,
  disabled = false,
  helperText,
  error,
}: FileDropzoneProps): JSX.Element {
  const theme = useTheme();
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): string | null => {
      // Check file type
      if (accept) {
        const acceptedTypes = accept.split(',').map((t) => t.trim().toLowerCase());
        const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
        const fileMimeType = file.type.toLowerCase();

        const isAccepted = acceptedTypes.some(
          (type) =>
            type === fileExtension ||
            type === fileMimeType ||
            (type.includes('/*') && fileMimeType.startsWith(type.replace('/*', '')))
        );

        if (!isAccepted) {
          return `File type not supported. Accepted: ${accept}`;
        }
      }

      // Check file size
      if (maxSize && file.size > maxSize) {
        return `File too large. Maximum size: ${formatFileSize(maxSize)}`;
      }

      return null;
    },
    [accept, maxSize]
  );

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || disabled) return;

      const newFiles: File[] = [];
      let lastError: string | null = null;

      for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i];
        if (!file) continue;
        const error = validateFile(file);
        if (error) {
          lastError = error;
        } else {
          newFiles.push(file);
          if (!multiple) break;
        }
      }

      if (lastError && newFiles.length === 0) {
        setValidationError(lastError);
      } else {
        setValidationError(null);
        if (newFiles.length > 0) {
          onFilesSelected?.(newFiles);
        }
      }
    },
    [disabled, multiple, onFilesSelected, validateFile]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
    // Reset input so same file can be selected again
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  const handleBrowseClick = () => {
    inputRef.current?.click();
  };

  const displayError = error || validationError;

  return (
    <Box>
      {/* Dropzone area */}
      <Box
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        sx={{
          border: `2px dashed ${
            isDragOver
              ? theme.palette.primary.main
              : displayError
                ? theme.palette.error.main
                : theme.palette.divider
          }`,
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          backgroundColor: isDragOver ? 'action.hover' : 'background.paper',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          transition: 'all 0.2s ease-in-out',
          '&:focus-within': {
            outline: `3px solid ${theme.palette.primary.main}`,
            outlineOffset: '2px',
          },
        }}
        onClick={handleBrowseClick}
        role="button"
        tabIndex={disabled ? -1 : 0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleBrowseClick();
          }
        }}
        aria-label="File upload dropzone"
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleInputChange}
          disabled={disabled}
          style={{ display: 'none' }}
          aria-describedby={displayError ? 'file-error' : undefined}
        />

        <CloudUploadIcon
          sx={{
            fontSize: 48,
            color: isDragOver ? 'primary.main' : 'text.secondary',
            mb: 1,
          }}
        />

        <Typography variant="body1" gutterBottom>
          {isDragOver
            ? 'Drop files here'
            : 'Drag & drop files here, or click to browse'}
        </Typography>

        {helperText && (
          <Typography variant="caption" color="text.secondary">
            {helperText}
          </Typography>
        )}

        <Box sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            disabled={disabled}
            onClick={(e) => {
              e.stopPropagation();
              handleBrowseClick();
            }}
          >
            Browse Files
          </Button>
        </Box>
      </Box>

      {/* Error message */}
      {displayError && (
        <Alert severity="error" sx={{ mt: 1 }} id="file-error">
          {displayError}
        </Alert>
      )}

      {/* File list */}
      {files.length > 0 && (
        <Box sx={{ mt: 2 }}>
          {files.map((file, index) => (
            <Box
              key={`${file.name}-${index}`}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1.5,
                borderRadius: 1,
                backgroundColor: 'grey.50',
                mb: 1,
              }}
            >
              {file.complete ? (
                <CheckCircleIcon color="success" />
              ) : (
                <InsertDriveFileIcon color="action" />
              )}

              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  variant="body2"
                  sx={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {file.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {formatFileSize(file.size)}
                </Typography>

                {file.progress !== undefined && file.progress < 100 && !file.error && (
                  <LinearProgress
                    variant="determinate"
                    value={file.progress}
                    sx={{ mt: 0.5, height: 4, borderRadius: 2 }}
                  />
                )}

                {file.error && (
                  <Typography variant="caption" color="error">
                    {file.error}
                  </Typography>
                )}
              </Box>

              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  onFileRemove?.(index);
                }}
                aria-label={`Remove ${file.name}`}
                sx={{
                  '&:focus': {
                    outline: `3px solid ${theme.palette.primary.main}`,
                    outlineOffset: '2px',
                  },
                }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}

export default FileDropzone;
