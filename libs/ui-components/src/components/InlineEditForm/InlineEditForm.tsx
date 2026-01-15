/**
 * InlineEditForm Component
 *
 * Read mode → Edit mode toggle with Save/Cancel buttons.
 * Used for inline editing of entity details.
 *
 * Accessibility:
 * - Focus moves to first input when entering edit mode
 * - Escape key cancels editing
 * - Tab order preserved
 */

import { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Button,
  TextField,
  CircularProgress,
  useTheme,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import type { ReactNode } from 'react';

/** Field definition for the form */
export interface InlineEditField {
  /** Unique field ID */
  id: string;
  /** Field label */
  label: string;
  /** Field type */
  type?: 'text' | 'email' | 'tel' | 'number' | 'textarea';
  /** Whether field is required */
  required?: boolean;
  /** Validation pattern */
  pattern?: RegExp;
  /** Error message for validation */
  errorMessage?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Max length */
  maxLength?: number;
  /** Number of rows (for textarea) */
  rows?: number;
}

/** InlineEditForm component props */
export interface InlineEditFormProps {
  /** Title displayed above the form */
  title?: string;
  /** Field definitions */
  fields: InlineEditField[];
  /** Current field values */
  values: Record<string, string>;
  /** Save handler - return true if save succeeded */
  onSave: (values: Record<string, string>) => Promise<boolean>;
  /** Cancel handler (optional) */
  onCancel?: () => void;
  /** Whether currently in edit mode (controlled) */
  editing?: boolean;
  /** Edit mode change handler (controlled) */
  onEditingChange?: (editing: boolean) => void;
  /** Whether save is in progress */
  saving?: boolean;
  /** Custom render for read mode value */
  renderValue?: (field: InlineEditField, value: string) => ReactNode;
  /** Whether edit button is disabled */
  editDisabled?: boolean;
}

/**
 * InlineEditForm provides inline editing with read/edit mode toggle.
 *
 * @example
 * ```tsx
 * <InlineEditForm
 *   title="Contact Information"
 *   fields={[
 *     { id: 'phone', label: 'Phone', type: 'tel', required: true },
 *     { id: 'email', label: 'Email', type: 'email' },
 *   ]}
 *   values={{ phone: '+254712345678', email: 'john@example.com' }}
 *   onSave={async (values) => {
 *     await updateFarmer(values);
 *     return true;
 *   }}
 * />
 * ```
 */
export function InlineEditForm({
  title,
  fields,
  values,
  onSave,
  onCancel,
  editing: controlledEditing,
  onEditingChange,
  saving = false,
  renderValue,
  editDisabled = false,
}: InlineEditFormProps): JSX.Element {
  const theme = useTheme();
  const [internalEditing, setInternalEditing] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const firstInputRef = useRef<HTMLInputElement>(null);

  // Use controlled or internal state
  const isEditing = controlledEditing ?? internalEditing;
  const setEditing = onEditingChange ?? setInternalEditing;

  // Initialize edit values when entering edit mode
  useEffect(() => {
    if (isEditing) {
      setEditValues({ ...values });
      setErrors({});
      // Focus first input after render
      setTimeout(() => {
        firstInputRef.current?.focus();
      }, 0);
    }
  }, [isEditing, values]);

  const handleEditClick = () => {
    setEditing(true);
  };

  const handleCancel = () => {
    setEditing(false);
    setEditValues({});
    setErrors({});
    onCancel?.();
  };

  const validateField = (field: InlineEditField, value: string): string | null => {
    if (field.required && !value.trim()) {
      return `${field.label} is required`;
    }
    if (field.pattern && value && !field.pattern.test(value)) {
      return field.errorMessage ?? `Invalid ${field.label.toLowerCase()}`;
    }
    return null;
  };

  const handleSave = async () => {
    // Validate all fields
    const newErrors: Record<string, string> = {};
    fields.forEach((field) => {
      const error = validateField(field, editValues[field.id] ?? '');
      if (error) {
        newErrors[field.id] = error;
      }
    });

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    const success = await onSave(editValues);
    if (success) {
      setEditing(false);
      setEditValues({});
      setErrors({});
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      handleCancel();
    }
  };

  const handleFieldChange = (fieldId: string, value: string) => {
    setEditValues((prev) => ({ ...prev, [fieldId]: value }));
    // Clear error when user starts typing
    if (errors[fieldId]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[fieldId];
        return next;
      });
    }
  };

  return (
    <Box onKeyDown={handleKeyDown}>
      {/* Header */}
      {title && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: 2,
          }}
        >
          <Typography variant="subtitle1" fontWeight={600}>
            {title}
          </Typography>
          {!isEditing && (
            <IconButton
              onClick={handleEditClick}
              disabled={editDisabled}
              aria-label="Edit"
              size="small"
              sx={{
                '&:focus': {
                  outline: `3px solid ${theme.palette.primary.main}`,
                  outlineOffset: '2px',
                },
              }}
            >
              <EditIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
      )}

      {/* Fields */}
      {isEditing ? (
        // Edit mode
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {fields.map((field, index) => (
            <TextField
              key={field.id}
              inputRef={index === 0 ? firstInputRef : undefined}
              label={field.label}
              type={field.type === 'textarea' ? undefined : field.type ?? 'text'}
              multiline={field.type === 'textarea'}
              rows={field.rows ?? 3}
              value={editValues[field.id] ?? ''}
              onChange={(e) => handleFieldChange(field.id, e.target.value)}
              error={!!errors[field.id]}
              helperText={errors[field.id]}
              required={field.required}
              placeholder={field.placeholder}
              slotProps={{
                htmlInput: {
                  maxLength: field.maxLength,
                },
              }}
              fullWidth
              size="small"
              sx={{
                '& .MuiOutlinedInput-root:focus-within': {
                  outline: `3px solid ${theme.palette.primary.main}`,
                  outlineOffset: '2px',
                },
              }}
            />
          ))}

          {/* Action buttons */}
          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', mt: 1 }}>
            <Button
              variant="outlined"
              onClick={handleCancel}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={saving}
              startIcon={saving ? <CircularProgress size={16} /> : undefined}
            >
              {saving ? 'Saving...' : 'Save'}
            </Button>
          </Box>
        </Box>
      ) : (
        // Read mode
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {fields.map((field) => (
            <Box key={field.id}>
              <Typography variant="caption" color="text.secondary">
                {field.label}
              </Typography>
              <Typography variant="body1">
                {renderValue
                  ? renderValue(field, values[field.id] ?? '')
                  : values[field.id] || '—'}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}

export default InlineEditForm;
