import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { fn } from '@storybook/test';
import { Box } from '@mui/material';
import { FileDropzone, UploadedFile } from './FileDropzone';

const meta: Meta<typeof FileDropzone> = {
  component: FileDropzone,
  title: 'Forms/FileDropzone',
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <Box sx={{ maxWidth: 500 }}>
        <Story />
      </Box>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof FileDropzone>;

/** Basic dropzone */
export const Basic: Story = {
  args: {
    onFilesSelected: fn(),
    helperText: 'Drag & drop or browse files',
  },
};

/** With file type restrictions */
export const RestrictedTypes: Story = {
  args: {
    accept: '.pdf,.doc,.docx',
    helperText: 'Supported formats: PDF, Word documents',
    onFilesSelected: fn(),
  },
};

/** With size limit */
export const WithSizeLimit: Story = {
  args: {
    accept: '.pdf,.doc,.docx',
    maxSize: 10 * 1024 * 1024, // 10MB
    helperText: 'Supported formats: PDF, Word. Max size: 10MB',
    onFilesSelected: fn(),
  },
};

/** Multiple files */
export const MultipleFiles: Story = {
  args: {
    multiple: true,
    helperText: 'You can select multiple files',
    onFilesSelected: fn(),
  },
};

/** With uploaded files */
export const WithFiles: Story = {
  args: {
    files: [
      { name: 'grading_model_v1.pdf', size: 1234567, type: 'application/pdf', complete: true },
      { name: 'farmer_data_export.xlsx', size: 2345678, type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', complete: true },
    ],
    onFilesSelected: fn(),
    onFileRemove: fn(),
  },
};

/** Upload in progress */
export const UploadInProgress: Story = {
  args: {
    files: [
      { name: 'large_document.pdf', size: 5432100, type: 'application/pdf', progress: 45 },
    ],
    onFilesSelected: fn(),
    onFileRemove: fn(),
  },
};

/** With upload error */
export const WithError: Story = {
  args: {
    files: [
      { name: 'corrupted_file.pdf', size: 123456, type: 'application/pdf', error: 'Upload failed. Please try again.' },
    ],
    onFilesSelected: fn(),
    onFileRemove: fn(),
  },
};

/** Validation error */
export const ValidationError: Story = {
  args: {
    accept: '.pdf',
    error: 'Please upload a PDF file',
    onFilesSelected: fn(),
  },
};

/** Disabled state */
export const Disabled: Story = {
  args: {
    disabled: true,
    helperText: 'File upload is currently disabled',
    onFilesSelected: fn(),
  },
};

/** Interactive example with simulated upload */
export const Interactive: Story = {
  render: function InteractiveDropzone() {
    const [files, setFiles] = useState<UploadedFile[]>([]);

    const handleFilesSelected = (selectedFiles: File[]) => {
      const newFiles: UploadedFile[] = selectedFiles.map((file) => ({
        name: file.name,
        size: file.size,
        type: file.type,
        progress: 0,
        file,
      }));

      setFiles((prev) => [...prev, ...newFiles]);

      // Simulate upload progress
      newFiles.forEach((_, index) => {
        const actualIndex = files.length + index;
        let progress = 0;
        const interval = setInterval(() => {
          progress += Math.random() * 20;
          if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
            setFiles((prev) =>
              prev.map((f, i) =>
                i === actualIndex ? { ...f, progress: 100, complete: true } : f
              )
            );
          } else {
            setFiles((prev) =>
              prev.map((f, i) => (i === actualIndex ? { ...f, progress } : f))
            );
          }
        }, 200);
      });
    };

    const handleRemove = (index: number) => {
      setFiles((prev) => prev.filter((_, i) => i !== index));
    };

    return (
      <FileDropzone
        accept=".pdf,.doc,.docx,.xls,.xlsx"
        maxSize={10 * 1024 * 1024}
        multiple
        files={files}
        onFilesSelected={handleFilesSelected}
        onFileRemove={handleRemove}
        helperText="Supported formats: PDF, Word, Excel. Max size: 10MB"
      />
    );
  },
};

/** Image upload */
export const ImageUpload: Story = {
  args: {
    accept: 'image/*',
    maxSize: 5 * 1024 * 1024,
    helperText: 'Upload images (JPG, PNG, GIF). Max size: 5MB',
    onFilesSelected: fn(),
  },
};
