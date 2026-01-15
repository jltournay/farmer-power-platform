import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { fn } from '@storybook/test';
import { Button, Box, Typography } from '@mui/material';
import { ConfirmationDialog } from './ConfirmationDialog';
import DeleteIcon from '@mui/icons-material/Delete';
import ArchiveIcon from '@mui/icons-material/Archive';

const meta: Meta<typeof ConfirmationDialog> = {
  component: ConfirmationDialog,
  title: 'Forms/ConfirmationDialog',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof ConfirmationDialog>;

/** Delete confirmation (destructive action) */
export const DeleteConfirmation: Story = {
  args: {
    open: true,
    title: 'Delete Farmer',
    message: 'Are you sure you want to delete John Kamau? This action cannot be undone and all associated data will be permanently removed.',
    confirmText: 'Delete',
    confirmColor: 'error',
    onClose: fn(),
    onConfirm: fn(),
  },
};

/** Warning confirmation */
export const WarningConfirmation: Story = {
  args: {
    open: true,
    title: 'Archive Region',
    message: 'Are you sure you want to archive Nyeri - High Altitude region? Farmers in this region will need to be reassigned.',
    confirmText: 'Archive',
    confirmColor: 'warning',
    onClose: fn(),
    onConfirm: fn(),
  },
};

/** Primary confirmation (non-destructive) */
export const PrimaryConfirmation: Story = {
  args: {
    open: true,
    title: 'Send Notification',
    message: 'This will send SMS notifications to 342 farmers in the selected region. Do you want to continue?',
    confirmText: 'Send',
    confirmColor: 'primary',
    onClose: fn(),
    onConfirm: fn(),
  },
};

/** Loading state */
export const Loading: Story = {
  args: {
    open: true,
    title: 'Delete Farmer',
    message: 'Are you sure you want to delete John Kamau?',
    confirmText: 'Delete',
    confirmColor: 'error',
    loading: true,
    onClose: fn(),
    onConfirm: fn(),
  },
};

/** Without warning icon */
export const NoIcon: Story = {
  args: {
    open: true,
    title: 'Confirm Selection',
    message: 'You have selected 15 farmers. Do you want to export their data?',
    confirmText: 'Export',
    showWarningIcon: false,
    onClose: fn(),
    onConfirm: fn(),
  },
};

/** With custom icon */
export const CustomIcon: Story = {
  args: {
    open: true,
    title: 'Archive Records',
    message: 'Move 23 quality events to archive? They will still be available in reports.',
    confirmText: 'Archive',
    confirmColor: 'warning',
    icon: <ArchiveIcon />,
    onClose: fn(),
    onConfirm: fn(),
  },
};

/** With rich message content */
export const RichMessage: Story = {
  args: {
    open: true,
    title: 'Delete Grading Model',
    message: (
      <Box>
        <Typography gutterBottom>
          You are about to delete the grading model <strong>"Kenya Tea Grade v2"</strong>.
        </Typography>
        <Typography color="error.main" variant="body2">
          Warning: 5 factories are currently using this model. They will be switched to the default model.
        </Typography>
      </Box>
    ),
    confirmText: 'Delete Model',
    confirmColor: 'error',
    onClose: fn(),
    onConfirm: fn(),
  },
};

/** Interactive example with trigger button */
export const Interactive: Story = {
  render: function InteractiveDialog() {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleConfirm = async () => {
      setLoading(true);
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setLoading(false);
      setOpen(false);
    };

    return (
      <Box>
        <Button
          variant="outlined"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={() => setOpen(true)}
        >
          Delete Farmer
        </Button>
        <ConfirmationDialog
          open={open}
          onClose={() => setOpen(false)}
          onConfirm={handleConfirm}
          title="Delete Farmer"
          message="Are you sure you want to delete John Kamau? This action cannot be undone."
          confirmText="Delete"
          confirmColor="error"
          loading={loading}
        />
      </Box>
    );
  },
};
