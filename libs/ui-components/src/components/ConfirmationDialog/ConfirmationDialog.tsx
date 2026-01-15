/**
 * ConfirmationDialog Component
 *
 * Modal dialog for confirming destructive actions.
 * Provides consistent UX for delete, remove, and other confirmation flows.
 *
 * Accessibility:
 * - Focus trapped within dialog
 * - Escape key closes dialog
 * - Focus returns to trigger element on close
 * - Proper ARIA attributes
 */

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  CircularProgress,
  IconButton,
  Box,
  useTheme,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import type { ReactNode } from 'react';

/** ConfirmationDialog component props */
export interface ConfirmationDialogProps {
  /** Whether dialog is open */
  open: boolean;
  /** Close handler */
  onClose: () => void;
  /** Confirm handler */
  onConfirm: () => void | Promise<void>;
  /** Dialog title */
  title: string;
  /** Dialog message */
  message: string | ReactNode;
  /** Confirm button text */
  confirmText?: string;
  /** Cancel button text */
  cancelText?: string;
  /** Confirm button color */
  confirmColor?: 'primary' | 'error' | 'warning';
  /** Whether confirmation is in progress */
  loading?: boolean;
  /** Whether to show warning icon */
  showWarningIcon?: boolean;
  /** Custom icon to show instead of warning */
  icon?: ReactNode;
}

/**
 * ConfirmationDialog provides a modal for confirming user actions.
 *
 * @example
 * ```tsx
 * <ConfirmationDialog
 *   open={deleteDialogOpen}
 *   onClose={() => setDeleteDialogOpen(false)}
 *   onConfirm={async () => {
 *     await deleteFarmer(farmerId);
 *     setDeleteDialogOpen(false);
 *   }}
 *   title="Delete Farmer"
 *   message="Are you sure you want to delete John Kamau? This action cannot be undone."
 *   confirmText="Delete"
 *   confirmColor="error"
 * />
 * ```
 */
export function ConfirmationDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmColor = 'primary',
  loading = false,
  showWarningIcon = true,
  icon,
}: ConfirmationDialogProps): JSX.Element {
  const theme = useTheme();

  const handleConfirm = async () => {
    await onConfirm();
  };

  const iconColor =
    confirmColor === 'error'
      ? theme.palette.error.main
      : confirmColor === 'warning'
        ? theme.palette.warning.main
        : theme.palette.primary.main;

  return (
    <Dialog
      open={open}
      onClose={loading ? undefined : onClose}
      aria-labelledby="confirmation-dialog-title"
      aria-describedby="confirmation-dialog-description"
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
        },
      }}
    >
      <DialogTitle
        id="confirmation-dialog-title"
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pr: 6,
        }}
      >
        {title}
        <IconButton
          aria-label="Close"
          onClick={onClose}
          disabled={loading}
          sx={{
            position: 'absolute',
            right: 8,
            top: 8,
            color: 'text.secondary',
            '&:focus': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent>
        <Box
          sx={{
            display: 'flex',
            gap: 2,
            alignItems: 'flex-start',
          }}
        >
          {(showWarningIcon || icon) && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 48,
                height: 48,
                borderRadius: '50%',
                backgroundColor:
                  confirmColor === 'error'
                    ? 'error.light'
                    : confirmColor === 'warning'
                      ? 'warning.light'
                      : 'primary.light',
                flexShrink: 0,
                '& svg': {
                  fontSize: 24,
                  color: iconColor,
                },
              }}
            >
              {icon ?? <WarningAmberIcon />}
            </Box>
          )}
          <DialogContentText
            id="confirmation-dialog-description"
            sx={{
              color: 'text.primary',
              flex: 1,
            }}
          >
            {message}
          </DialogContentText>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={onClose}
          disabled={loading}
          variant="outlined"
          sx={{
            '&:focus': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        >
          {cancelText}
        </Button>
        <Button
          onClick={handleConfirm}
          disabled={loading}
          variant="contained"
          color={confirmColor}
          startIcon={loading ? <CircularProgress size={16} color="inherit" /> : undefined}
          sx={{
            '&:focus': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        >
          {loading ? 'Processing...' : confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default ConfirmationDialog;
