import { Box, TextField, Button, ButtonGroup } from '@mui/material';

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
}

function getPresetRange(days: number): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - days);
  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  };
}

export function DateRangePicker({ startDate, endDate, onStartDateChange, onEndDateChange }: DateRangePickerProps): JSX.Element {
  const applyPreset = (days: number) => {
    const { start, end } = getPresetRange(days);
    onStartDateChange(start);
    onEndDateChange(end);
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
      <ButtonGroup size="small" variant="outlined">
        <Button onClick={() => applyPreset(7)}>7d</Button>
        <Button onClick={() => applyPreset(14)}>14d</Button>
        <Button onClick={() => applyPreset(30)}>30d</Button>
        <Button onClick={() => applyPreset(90)}>90d</Button>
      </ButtonGroup>
      <TextField
        type="date"
        label="Start"
        size="small"
        value={startDate}
        onChange={(e) => onStartDateChange(e.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <TextField
        type="date"
        label="End"
        size="small"
        value={endDate}
        onChange={(e) => onEndDateChange(e.target.value)}
        slotProps={{ inputLabel: { shrink: true } }}
      />
    </Box>
  );
}
