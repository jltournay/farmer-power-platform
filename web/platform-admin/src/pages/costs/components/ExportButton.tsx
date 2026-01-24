import { IconButton, Tooltip } from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';

interface ExportButtonProps {
  data: Record<string, unknown>[];
  filename: string;
  disabled?: boolean;
}

function exportToCsv(data: Record<string, unknown>[], filename: string) {
  if (data.length === 0) return;
  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map((row) =>
      headers.map((h) => JSON.stringify(row[h] ?? '')).join(',')
    ),
  ].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function ExportButton({ data, filename, disabled }: ExportButtonProps): JSX.Element {
  return (
    <Tooltip title="Export CSV">
      <span>
        <IconButton
          onClick={() => exportToCsv(data, filename)}
          disabled={disabled || data.length === 0}
          size="large"
          sx={{ minWidth: 48, minHeight: 48 }}
        >
          <FileDownloadIcon />
        </IconButton>
      </span>
    </Tooltip>
  );
}
