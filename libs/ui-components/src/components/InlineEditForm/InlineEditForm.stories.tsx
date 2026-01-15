import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { fn } from '@storybook/test';
import { Paper } from '@mui/material';
import { InlineEditForm } from './InlineEditForm';

const contactFields = [
  { id: 'phone', label: 'Phone', type: 'tel' as const, required: true },
  { id: 'email', label: 'Email', type: 'email' as const },
  { id: 'address', label: 'Address', type: 'textarea' as const, rows: 2 },
];

const meta: Meta<typeof InlineEditForm> = {
  component: InlineEditForm,
  title: 'Forms/InlineEditForm',
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <Paper sx={{ p: 3, maxWidth: 400 }}>
        <Story />
      </Paper>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof InlineEditForm>;

/** Read mode (default view) */
export const ReadMode: Story = {
  args: {
    title: 'Contact Information',
    fields: contactFields,
    values: {
      phone: '+254712345678',
      email: 'john.kamau@example.com',
      address: 'P.O. Box 123, Nyeri, Kenya',
    },
    onSave: fn(),
  },
};

/** Edit mode */
export const EditMode: Story = {
  args: {
    title: 'Contact Information',
    fields: contactFields,
    values: {
      phone: '+254712345678',
      email: 'john.kamau@example.com',
      address: 'P.O. Box 123, Nyeri, Kenya',
    },
    editing: true,
    onSave: fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      return true;
    }),
  },
};

/** With validation errors */
export const WithValidation: Story = {
  args: {
    title: 'Contact Information',
    fields: [
      { id: 'phone', label: 'Phone', type: 'tel' as const, required: true },
      {
        id: 'email',
        label: 'Email',
        type: 'email' as const,
        pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        errorMessage: 'Please enter a valid email address',
      },
    ],
    values: { phone: '', email: '' },
    editing: true,
    onSave: fn(async () => false),
  },
};

/** Saving state */
export const Saving: Story = {
  args: {
    title: 'Contact Information',
    fields: contactFields,
    values: {
      phone: '+254712345678',
      email: 'john.kamau@example.com',
      address: 'P.O. Box 123, Nyeri, Kenya',
    },
    editing: true,
    saving: true,
    onSave: fn(),
  },
};

/** Interactive example */
export const Interactive: Story = {
  render: function InteractiveForm() {
    const [values, setValues] = useState({
      phone: '+254712345678',
      email: 'john.kamau@example.com',
      address: 'P.O. Box 123, Nyeri, Kenya',
    });
    const [saving, setSaving] = useState(false);

    const handleSave = async (newValues: Record<string, string>) => {
      setSaving(true);
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setValues(newValues as typeof values);
      setSaving(false);
      return true;
    };

    return (
      <InlineEditForm
        title="Contact Information"
        fields={contactFields}
        values={values}
        onSave={handleSave}
        saving={saving}
      />
    );
  },
};

/** Without title */
export const NoTitle: Story = {
  args: {
    fields: [
      { id: 'name', label: 'Name', required: true },
      { id: 'phone', label: 'Phone', type: 'tel' as const },
    ],
    values: { name: 'John Kamau', phone: '+254712345678' },
    onSave: fn(),
  },
};

/** With empty values */
export const EmptyValues: Story = {
  args: {
    title: 'Contact Information',
    fields: contactFields,
    values: { phone: '', email: '', address: '' },
    onSave: fn(),
  },
};

/** Edit disabled */
export const EditDisabled: Story = {
  args: {
    title: 'System Information',
    fields: [
      { id: 'id', label: 'Farmer ID' },
      { id: 'created', label: 'Created At' },
    ],
    values: { id: 'FRM-001-2024', created: 'January 15, 2024' },
    onSave: fn(),
    editDisabled: true,
  },
};
