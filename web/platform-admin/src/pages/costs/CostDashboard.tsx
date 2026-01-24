/**
 * Cost Dashboard Page (Story 9.10b)
 *
 * Platform cost monitoring with tabs for Overview, LLM, Documents, and Embeddings.
 * Provides budget configuration and CSV export.
 */

import { useState, useMemo, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, Button, Snackbar, Alert } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import { DateRangePicker } from './components/DateRangePicker';
import { ExportButton } from './components/ExportButton';
import { BudgetConfigDialog } from './components/BudgetConfigDialog';
import { OverviewTab } from './tabs/OverviewTab';
import { LlmTab } from './tabs/LlmTab';
import { DocumentsTab } from './tabs/DocumentsTab';
import { EmbeddingsTab } from './tabs/EmbeddingsTab';
import { getBudgetStatus } from '../../api/costs';
import type { BudgetStatusResponse } from '../../api/types';

function getDefaultDateRange(): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 30);
  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  };
}

const TAB_NAMES = ['overview', 'llm', 'documents', 'embeddings'] as const;

/**
 * Cost dashboard page component with tabbed views.
 */
export function CostDashboard(): JSX.Element {
  const defaultRange = useMemo(() => getDefaultDateRange(), []);
  const [startDate, setStartDate] = useState(defaultRange.start);
  const [endDate, setEndDate] = useState(defaultRange.end);
  const [activeTab, setActiveTab] = useState(0);
  const [budgetDialogOpen, setBudgetDialogOpen] = useState(false);
  const [budgetStatus, setBudgetStatus] = useState<BudgetStatusResponse | null>(null);
  const [tabExportData, setTabExportData] = useState<Record<number, Record<string, unknown>[]>>({});
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const handleExportData = useCallback((tabIndex: number, data: Record<string, unknown>[]) => {
    setTabExportData((prev) => ({ ...prev, [tabIndex]: data }));
  }, []);

  const handleBudgetClick = async () => {
    try {
      const status = await getBudgetStatus();
      setBudgetStatus(status);
      setBudgetDialogOpen(true);
    } catch {
      setBudgetDialogOpen(true);
    }
  };

  const handleBudgetSuccess = () => {
    setSnackbar({ open: true, message: 'Budget thresholds updated successfully', severity: 'success' });
  };

  const exportData = tabExportData[activeTab] ?? [];
  const exportFilename = `costs-${TAB_NAMES[activeTab]}-${startDate}-to-${endDate}.csv`;

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h4" component="h1">
          Platform Costs
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ExportButton data={exportData} filename={exportFilename} disabled={exportData.length === 0} />
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={handleBudgetClick}
            sx={{ minHeight: 48 }}
          >
            Budget
          </Button>
        </Box>
      </Box>

      {/* Date Range */}
      <Box sx={{ mb: 2 }}>
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
          <Tab label="Overview" />
          <Tab label="LLM" />
          <Tab label="Documents" />
          <Tab label="Embeddings" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 0 && <OverviewTab startDate={startDate} endDate={endDate} onExportData={(data) => handleExportData(0, data)} />}
      {activeTab === 1 && <LlmTab startDate={startDate} endDate={endDate} onExportData={(data) => handleExportData(1, data)} />}
      {activeTab === 2 && <DocumentsTab startDate={startDate} endDate={endDate} onExportData={(data) => handleExportData(2, data)} />}
      {activeTab === 3 && <EmbeddingsTab startDate={startDate} endDate={endDate} onExportData={(data) => handleExportData(3, data)} />}

      {/* Budget Dialog */}
      <BudgetConfigDialog
        open={budgetDialogOpen}
        onClose={() => setBudgetDialogOpen(false)}
        budgetStatus={budgetStatus}
        onSuccess={handleBudgetSuccess}
      />

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
