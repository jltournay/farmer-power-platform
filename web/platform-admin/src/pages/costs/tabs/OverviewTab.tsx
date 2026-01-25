import { useState, useEffect, useRef } from 'react';
import { Box, Grid2 as Grid, Alert, Button, CircularProgress, Typography } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { getCostSummary, getDailyTrend, getCurrentDayCost, getBudgetStatus } from '../../../api/costs';
import type { CostSummaryResponse, DailyTrendResponse, CurrentDayCostResponse, BudgetStatusResponse } from '../../../api/types';
import { MetricCard } from '../components/MetricCard';
import { BudgetBar } from '../components/BudgetBar';
import { CostTrendChart } from '../components/CostTrendChart';
import { CostBreakdownCards } from '../components/CostBreakdownCards';

interface OverviewTabProps {
  startDate: string;
  endDate: string;
  onExportData?: (data: Record<string, unknown>[]) => void;
}

export function OverviewTab({ startDate, endDate, onExportData }: OverviewTabProps): JSX.Element {
  const [summary, setSummary] = useState<CostSummaryResponse | null>(null);
  const [trend, setTrend] = useState<DailyTrendResponse | null>(null);
  const [todayCost, setTodayCost] = useState<CurrentDayCostResponse | null>(null);
  const [budget, setBudget] = useState<BudgetStatusResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Ref for polling interval
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch all data on mount and when date range changes
  useEffect(() => {
    let cancelled = false;

    const fetchAllData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [summaryData, trendData, todayData, budgetData] = await Promise.all([
          getCostSummary({ start_date: startDate, end_date: endDate }),
          getDailyTrend(30),
          getCurrentDayCost(),
          getBudgetStatus(),
        ]);

        if (!cancelled) {
          setSummary(summaryData);
          setTrend(trendData);
          setTodayCost(todayData);
          setBudget(budgetData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load data');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchAllData();

    // Set up polling for today's cost (every 60 seconds)
    pollingRef.current = setInterval(async () => {
      if (cancelled) return;
      try {
        const todayData = await getCurrentDayCost();
        if (!cancelled) {
          setTodayCost(todayData);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 60000);

    return () => {
      cancelled = true;
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [startDate, endDate]);

  // Report export data when trend loads
  // Note: onExportData should be memoized in parent to prevent infinite re-renders
  useEffect(() => {
    if (trend && onExportData) {
      onExportData(trend.entries.map((e) => ({
        date: e.entry_date,
        total_cost_usd: e.total_cost_usd,
        llm_cost_usd: e.llm_cost_usd,
        document_cost_usd: e.document_cost_usd,
        embedding_cost_usd: e.embedding_cost_usd,
      })));
    }
  }, [trend, onExportData]);

  const formatTime = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const todayByType = todayCost?.by_type
    ? Object.entries(todayCost.by_type)
        .map(([type, cost]) => `${type}: $${parseFloat(cost).toFixed(2)}`)
        .join(' | ')
    : '';

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert
        severity="error"
        action={
          <Button size="small" startIcon={<RefreshIcon />} onClick={() => window.location.reload()}>
            Retry
          </Button>
        }
      >
        {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Metric Cards Row */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <MetricCard
            label="Total Cost"
            value={summary ? `$${parseFloat(summary.total_cost_usd).toFixed(2)}` : '-'}
            subtitle={summary ? `${summary.total_requests.toLocaleString()} requests` : undefined}
            loading={false}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <MetricCard
            label="Today (Live)"
            value={todayCost ? `$${parseFloat(todayCost.total_cost_usd).toFixed(2)}` : '-'}
            subtitle={todayCost ? `Updated ${formatTime(todayCost.updated_at)}${todayByType ? ` · ${todayByType}` : ''}` : undefined}
            loading={false}
          />
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5, ml: 1 }}>
            <CircularProgress size={12} sx={{ mr: 0.5 }} />
            <Typography variant="caption" color="text.secondary">Polling every 60s</Typography>
          </Box>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Box>
            <MetricCard
              label="Budget Status"
              value={budget ? `Monthly: ${budget.monthly_utilization_percent.toFixed(0)}%` : '-'}
              subtitle={budget ? `$${parseFloat(budget.monthly_total_usd).toFixed(0)} / $${parseFloat(budget.monthly_threshold_usd).toFixed(0)}` : undefined}
              loading={false}
            />
            {budget && (
              <Box sx={{ px: 2, pb: 1 }}>
                <BudgetBar
                  label="Daily"
                  utilization={budget.daily_utilization_percent}
                  current={parseFloat(budget.daily_total_usd).toFixed(2)}
                  threshold={parseFloat(budget.daily_threshold_usd).toFixed(2)}
                />
              </Box>
            )}
          </Box>
        </Grid>
      </Grid>

      {/* Trend Chart */}
      <CostTrendChart
        entries={trend?.entries ?? []}
        loading={false}
        dataAvailableFrom={trend?.data_available_from}
      />

      {/* Cost Breakdown */}
      <CostBreakdownCards
        breakdown={summary?.by_type ?? []}
        loading={false}
      />
    </Box>
  );
}
