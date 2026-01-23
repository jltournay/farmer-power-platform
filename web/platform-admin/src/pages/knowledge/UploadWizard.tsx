/**
 * Upload Wizard Page
 *
 * 3-step wizard for uploading knowledge documents:
 * Step 1: File selection & metadata
 * Step 2: Processing & content preview
 * Step 3: Save with status selection
 *
 * Story 9.9b (AC 9.9b.2, AC 9.9b.3, AC 9.9b.4, AC 9.9b.5)
 */

import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Typography,
  TextField,
  MenuItem,
  Paper,
  Alert,
  Chip,
  Radio,
  RadioGroup,
  FormControlLabel,
  Snackbar,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { PageHeader } from '@fp/ui-components';
import {
  uploadDocument,
  getDocument,
  stageDocument,
  activateDocument,
  type KnowledgeDomain,
  type DocumentDetail,
  type ExtractionJobStatus,
  KNOWLEDGE_DOMAIN_OPTIONS,
  getDomainLabel,
} from '@/api';
import { ExtractionProgress } from './components/ExtractionProgress';
import { ContentPreview } from './components/ContentPreview';

const STEPS = ['Upload', 'Preview', 'Save'];

const ACCEPTED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/markdown', 'text/plain'];
const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.md', '.txt'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

const metadataSchema = z.object({
  title: z.string().min(1, 'Title is required').max(500),
  domain: z.enum(['plant_diseases', 'tea_cultivation', 'weather_patterns', 'quality_standards', 'regional_context'] as const),
  author: z.string().optional(),
  source: z.string().optional(),
  region: z.string().optional(),
});

type MetadataForm = z.infer<typeof metadataSchema>;

/**
 * Upload wizard page component.
 */
export function UploadWizard(): JSX.Element {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [manualContent, setManualContent] = useState('');
  const [useManualInput, setUseManualInput] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step 2 state
  const [jobStatus, setJobStatus] = useState<ExtractionJobStatus | null>(null);
  const [extractedDocument, setExtractedDocument] = useState<DocumentDetail | null>(null);
  const [editedContent, setEditedContent] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [extractionComplete, setExtractionComplete] = useState(false);

  // Step 3 state
  const [saveStatus, setSaveStatus] = useState<'draft' | 'staged' | 'active'>('staged');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  const { control, handleSubmit, formState: { errors, isValid }, getValues } = useForm<MetadataForm>({
    resolver: zodResolver(metadataSchema),
    mode: 'onChange',
    defaultValues: {
      title: '',
      domain: undefined,
      author: '',
      source: '',
      region: '',
    },
  });

  // File handling
  const validateFile = (f: File): string | null => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext) && !ACCEPTED_TYPES.includes(f.type)) {
      return `Unsupported file type. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`;
    }
    if (f.size > MAX_FILE_SIZE) {
      return 'File too large. Maximum size is 50MB.';
    }
    return null;
  };

  const handleFileSelect = (f: File) => {
    const error = validateFile(f);
    if (error) {
      setFileError(error);
      return;
    }
    setFile(f);
    setFileError(null);
    setUseManualInput(false);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      const error = validateFile(droppedFile);
      if (error) {
        setFileError(error);
        return;
      }
      setFile(droppedFile);
      setFileError(null);
      setUseManualInput(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
  }, []);

  // Step transitions
  const canProceedStep1 = (file || (useManualInput && manualContent.trim())) && isValid;

  const handleStep1Continue = handleSubmit(async (formData) => {
    setUploadError(null);

    if (useManualInput) {
      // Manual content - skip extraction, go directly to step 3
      setExtractedDocument({
        id: '',
        document_id: '',
        version: 1,
        title: formData.title,
        domain: formData.domain,
        content: manualContent,
        status: 'draft',
        metadata: {
          author: formData.author || '',
          source: formData.source || '',
          region: formData.region || '',
          season: '',
          tags: [],
        },
        source_file: null,
        change_summary: '',
        pinecone_namespace: '',
        content_hash: '',
        created_at: null,
        updated_at: null,
      });
      setExtractionComplete(true);
      setActiveStep(1);
      // Immediately go to step 3 for manual content
      setTimeout(() => setActiveStep(2), 100);
      return;
    }

    // File upload
    if (!file) return;

    try {
      const result = await uploadDocument(file, {
        title: formData.title,
        domain: formData.domain as KnowledgeDomain,
        author: formData.author || undefined,
        source: formData.source || undefined,
        region: formData.region || undefined,
      });
      setJobStatus(result);
      setActiveStep(1);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    }
  });

  const handleExtractionComplete = useCallback(async () => {
    if (!jobStatus) return;
    try {
      const doc = await getDocument(jobStatus.document_id);
      setExtractedDocument(doc);
      setExtractionComplete(true);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Failed to load extracted document');
    }
  }, [jobStatus]);

  const handleExtractionError = useCallback((error: string) => {
    setUploadError(error);
  }, []);

  const handleSave = async () => {
    if (!extractedDocument) return;
    setSaving(true);
    setSaveError(null);

    try {
      const docId = extractedDocument.document_id;

      if (saveStatus === 'staged' && extractedDocument.status === 'draft') {
        await stageDocument(docId);
      } else if (saveStatus === 'active') {
        if (extractedDocument.status === 'draft') {
          await stageDocument(docId);
        }
        await activateDocument(docId);
      }

      setSnackbarOpen(true);
      setTimeout(() => {
        navigate(`/knowledge/${docId}`);
      }, 1000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const confidence = extractedDocument?.source_file?.extraction_confidence ?? 1;
  const isLowConfidence = confidence < 0.8;
  const confidencePercent = Math.round(confidence * 100);

  const getConfidenceColor = (): 'success' | 'warning' | 'error' => {
    if (confidencePercent >= 80) return 'success';
    if (confidencePercent >= 60) return 'warning';
    return 'error';
  };

  return (
    <Box>
      <PageHeader title="Upload New Document" />

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {STEPS.map((label, index) => (
          <Step key={label}>
            <StepLabel aria-current={index === activeStep ? 'step' : undefined}>
              {label}
            </StepLabel>
          </Step>
        ))}
      </Stepper>

      {/* Step 1: File & Metadata */}
      {activeStep === 0 && (
        <Box>
          {!useManualInput && (
            <Paper
              variant="outlined"
              sx={{
                p: 4,
                textAlign: 'center',
                border: dragActive ? '2px dashed' : '2px dashed',
                borderColor: dragActive ? 'primary.main' : 'grey.300',
                bgcolor: dragActive ? 'action.hover' : 'transparent',
                cursor: 'pointer',
                mb: 2,
              }}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  fileInputRef.current?.click();
                }
              }}
              tabIndex={0}
              role="button"
              aria-label="Drop zone for file upload. Click or press Enter to browse files."
            >
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_EXTENSIONS.join(',')}
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileSelect(f);
                }}
              />
              <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
              <Typography variant="body1" gutterBottom>
                {file ? file.name : 'Drag & drop your file here'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {file
                  ? `${(file.size / 1024 / 1024).toFixed(1)} MB`
                  : `Supported: PDF, DOCX, MD, TXT - Max size: 50MB`}
              </Typography>
            </Paper>
          )}

          {fileError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {fileError}
            </Alert>
          )}

          {!useManualInput && (
            <Box sx={{ textAlign: 'center', my: 2 }}>
              <Typography variant="body2" color="text.secondary">OR</Typography>
              <Button variant="text" onClick={() => { setUseManualInput(true); setFile(null); }}>
                Write content directly
              </Button>
            </Box>
          )}

          {useManualInput && (
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="subtitle2">Write content directly</Typography>
                <Button size="small" onClick={() => { setUseManualInput(false); setManualContent(''); }}>
                  Upload file instead
                </Button>
              </Box>
              <TextField
                multiline
                rows={8}
                fullWidth
                placeholder="Enter document content in markdown format..."
                value={manualContent}
                onChange={(e) => setManualContent(e.target.value)}
              />
            </Box>
          )}

          <Typography variant="subtitle1" sx={{ mt: 3, mb: 2 }}>Document Details</Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Controller
              name="title"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Title"
                  required
                  fullWidth
                  error={!!errors.title}
                  helperText={errors.title?.message}
                />
              )}
            />

            <Controller
              name="domain"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="Domain"
                  required
                  fullWidth
                  error={!!errors.domain}
                  helperText={errors.domain?.message}
                >
                  {KNOWLEDGE_DOMAIN_OPTIONS.map(opt => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </TextField>
              )}
            />

            <Controller
              name="author"
              control={control}
              render={({ field }) => (
                <TextField {...field} label="Author" fullWidth />
              )}
            />

            <Controller
              name="source"
              control={control}
              render={({ field }) => (
                <TextField {...field} label="Source" fullWidth placeholder="e.g., TBK Research Paper, Field Study" />
              )}
            />

            <Controller
              name="region"
              control={control}
              render={({ field }) => (
                <TextField {...field} label="Region (optional)" fullWidth />
              )}
            />
          </Box>

          {uploadError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {uploadError}
            </Alert>
          )}

          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
            <Button onClick={() => navigate('/knowledge')}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleStep1Continue}
              disabled={!canProceedStep1}
            >
              Continue
            </Button>
          </Box>
        </Box>
      )}

      {/* Step 2: Processing & Preview */}
      {activeStep === 1 && (
        <Box>
          {!extractionComplete && jobStatus && (
            <Box>
              <Typography variant="h6" gutterBottom>
                {getValues('title') || 'Processing document...'}
              </Typography>
              <ExtractionProgress
                documentId={jobStatus.document_id}
                jobId={jobStatus.job_id}
                onComplete={handleExtractionComplete}
                onError={handleExtractionError}
              />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                This may take 1-2 minutes for large documents
              </Typography>
            </Box>
          )}

          {extractionComplete && extractedDocument && (
            <Box>
              <Typography variant="h6" gutterBottom>
                {extractedDocument.title}
              </Typography>

              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                {extractedDocument.source_file && (
                  <>
                    <Chip
                      label={`Confidence: ${confidencePercent}%`}
                      size="small"
                      color={getConfidenceColor()}
                    />
                    <Chip
                      label={`Method: ${extractedDocument.source_file.extraction_method}`}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      label={`Pages: ${extractedDocument.source_file.page_count}`}
                      size="small"
                      variant="outlined"
                    />
                  </>
                )}
              </Box>

              {isLowConfidence && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    Extraction confidence is low ({confidencePercent}%). Some content may be missing or incorrect.
                  </Typography>
                  <Typography variant="body2">
                    You can edit the content below, or continue if the content looks acceptable.
                  </Typography>
                </Alert>
              )}

              {isEditing ? (
                <Box sx={{ mb: 2 }}>
                  <TextField
                    multiline
                    rows={15}
                    fullWidth
                    value={editedContent ?? extractedDocument.content}
                    onChange={(e) => setEditedContent(e.target.value)}
                  />
                  <Button size="small" onClick={() => setIsEditing(false)} sx={{ mt: 1 }}>
                    Done editing
                  </Button>
                </Box>
              ) : (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle2">Extracted Content</Typography>
                    <Button size="small" onClick={() => setIsEditing(true)}>Edit</Button>
                  </Box>
                  <ContentPreview content={editedContent ?? extractedDocument.content} />
                </Box>
              )}

              {uploadError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {uploadError}
                </Alert>
              )}

              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
                <Button onClick={() => { setActiveStep(0); setExtractionComplete(false); setJobStatus(null); }}>
                  Back
                </Button>
                <Button variant="contained" onClick={() => setActiveStep(2)}>
                  Continue
                </Button>
              </Box>
            </Box>
          )}
        </Box>
      )}

      {/* Step 3: Save */}
      {activeStep === 2 && extractedDocument && (
        <Box>
          <Typography variant="h6" gutterBottom>Document Summary</Typography>

          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
              <Typography variant="body2"><strong>Title:</strong> {extractedDocument.title}</Typography>
              <Typography variant="body2"><strong>Domain:</strong> {getDomainLabel(extractedDocument.domain)}</Typography>
              <Typography variant="body2"><strong>Author:</strong> {extractedDocument.metadata?.author || '-'}</Typography>
              <Typography variant="body2"><strong>Source:</strong> {extractedDocument.metadata?.source || '-'}</Typography>
              {extractedDocument.source_file && (
                <>
                  <Typography variant="body2"><strong>Pages:</strong> {extractedDocument.source_file.page_count}</Typography>
                  <Typography variant="body2"><strong>Extraction:</strong> {extractedDocument.source_file.extraction_method} ({confidencePercent}%)</Typography>
                </>
              )}
              <Typography variant="body2">
                <strong>Word count:</strong> ~{(editedContent ?? extractedDocument.content).split(/\s+/).length.toLocaleString()} words
              </Typography>
            </Box>
          </Paper>

          <Typography variant="subtitle1" gutterBottom>Save As</Typography>
          <RadioGroup value={saveStatus} onChange={(e) => setSaveStatus(e.target.value as typeof saveStatus)}>
            <FormControlLabel
              value="draft"
              control={<Radio />}
              label={
                <Box>
                  <Typography variant="body2"><strong>Draft</strong> - Save for later editing. Not visible to AI agents.</Typography>
                </Box>
              }
            />
            <FormControlLabel
              value="staged"
              control={<Radio />}
              label={
                <Box>
                  <Typography variant="body2"><strong>Staged</strong> (Recommended) - Ready for review. Test with AI first.</Typography>
                </Box>
              }
            />
            <FormControlLabel
              value="active"
              control={<Radio />}
              label={
                <Box>
                  <Typography variant="body2"><strong>Active</strong> (Requires approval) - Immediately available to AI agents.</Typography>
                </Box>
              }
            />
          </RadioGroup>

          {saveError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {saveError}
            </Alert>
          )}

          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
            <Button onClick={() => setActiveStep(1)}>Back</Button>
            <Button variant="contained" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : `Save as ${saveStatus.charAt(0).toUpperCase() + saveStatus.slice(1)}`}
            </Button>
          </Box>
        </Box>
      )}

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message="Document saved successfully"
      />
    </Box>
  );
}
