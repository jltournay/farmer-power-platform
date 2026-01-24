import { useState, useEffect, useCallback } from 'react';
import { Box, Grid, Alert, Button, CircularProgress, Typography } from '@mui/material';
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
}

export function OverviewTab({ startDate, endDate }: OverviewTabProps): JSX.Element {
  const [summary, setSummary] = useState<CostSummaryResponse | null>(null);
  const [trend, setTrend] = useState<DailyTrendResponse | null>(null);
  const [todayCost, setTodayCost] = useState<CurrentDayCostResponse | null>(null);
  const [budget, setBudget] = useState<BudgetStatusResponse | null>(null);

  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingTrend, setLoadingTrend] = useState(true);
  const [loadingToday, setLoadingToday] = useState(true);
  const [loadingBudget, setLoadingBudget] = useState(true);

  const [errorSummary, setErrorSummary] = useState<string | null>(null);
  const [errorTrend, setErrorTrend] = useState<string | null>(null);
  const [errorToday, setErrorToday] = useState<string | null>(null);
  const [errorBudget, setErrorBudget] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setLoadingSummary(true);
    setErrorSummary(null);
    try {
      const data = await getCostSummary({ start_date: startDate, end_date: endDate });
      setSummary(data);
    } catch (err) {
      setErrorSummary(err instanceof Error ? err.message : 'Failed to load cost summary');
    } finally {
      setLoadingSummary(false);
    }
  }, [startDate, endDate]);

  const fetchTrend = useCallback(async () => {
    setLoadingTrend(true);
    setErrorTrend(null);
    try {
      // Calculate days from date range
      const start = new Date(startDate);
      const end = new Date(endDate);
      const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
      const data = await getDailyTrend(days > 0 ? days : 30);
      setTrend(data);
    } catch (err) {
      setErrorTrend(err instanceof Error ? err.message : 'Failed to load trend data');
    } finally {
      setLoadingTrend(false);
    }
  }, [startDate, endDate]);

  const fetchToday = useCallback(async () => {
    setLoadingToday(true);
    setErrorToday(null);
    try {
      const data = await getCurrentDayCost();
      setTodayCost(data);
    } catch (err) {
      setErrorToday(err instanceof Error ? err.message : 'Failed to load today\'s cost');
    } finally {
      setLoadingToday(false);
    }
  }, []);

  const fetchBudget = useCallback(async () => {
    setLoadingBudget(true);
    setErrorBudget(null);
    try {
      const data = await getBudgetStatus();
      setBudget(data);
    } catch (err) {
      setErrorBudget(err instanceof Error ? err.message : 'Failed to load budget status');
    } finally {
      setLoadingBudget(false);
    }
  }, []);

  // Fetch summary and trend on date range change
  useEffect(() => {
    fetchSummary();
    fetchTrend();
  }, [fetchSummary, fetchTrend]);

  // Fetch budget once
  useEffect(() => {
    fetchBudget();
  }, [fetchBudget]);

  // Poll today's cost every 60s
  useEffect(() => {
    fetchToday();
    const interval = setInterval(fetchToday, 60000);
    return () => clearInterval(interval);
  }, [fetchToday]);

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

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Metric Cards Row */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          {errorSummary ? (
            <Alert severity="error" action={<Button size="small" onClick={fetchSummary}>Retry</Button>}>
              {errorSummary}
            </Alert>
          ) : (
            <MetricCard
              label="Total Cost"
              value={summary ? `$${parseFloat(summary.total_cost_usd).toFixed(2)}` : '-'}
              subtitle={summary ? `${summary.total_requests.toLocaleString()} requests` : undefined}
              loading={loadingSummary}
            />
          )}
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          {errorToday ? (
            <Alert severity="error" action={<Button size="small" onClick={fetchToday}>Retry</Button>}>
              {errorToday}
            </Alert>
          ) : (
            <MetricCard
              label="Today (Live)"
              value={todayCost ? `$${parseFloat(todayCost.total_cost_usd).toFixed(2)}` : '-'}
              subtitle={todayCost ? `Updated ${formatTime(todayCost.updated_at)}${todayByType ? ` · ${todayByType}` : ''}` : undefined}
              loading={loadingToday}
            />
          )}
          {!loadingToday && !errorToday && (
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5, ml: 1 }}>
              <CircularProgress size={12} sx={{ mr: 0.5 }} />
              <Typography variant="caption" color="text.secondary">Polling every 60s</Typography>
            </Box>
          )}
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          {errorBudget ? (
            <Alert severity="error" action={<Button size="small" onClick={fetchBudget}>Retry</Button>}>
              {errorBudget}
            </Alert>
          ) : (
            <Box>
              <MetricCard
                label="Budget Status"
                value={budget ? `Monthly: ${budget.monthly_utilization_percent.toFixed(0)}%` : '-'}
                subtitle={budget ? `$${parseFloat(budget.monthly_total_usd).toFixed(0)} / $${parseFloat(budget.monthly_threshold_usd).toFixed(0)}` : undefined}
                loading={loadingBudget}
              />
              {budget && !loadingBudget && (
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
          )}
        </Grid>
      </Grid>

      {/* Trend Chart */}
      {errorTrend ? (
        <Alert severity="error" action={<Button size="small" startIcon={<RefreshIcon />} onClick={fetchTrend}>Retry</Button>}>
          {errorTrend}
        </Alert>
      ) : (
        <CostTrendChart
          entries={trend?.entries ?? []}
          loading={loadingTrend}
          dataAvailableFrom={trend?.data_available_from}
        />
      )}

      {/* Cost Breakdown */}
      {errorSummary ? null : (
        <CostBreakdownCards
          breakdown={summary?.by_type ?? []}
          loading={loadingSummary}
        />
      )}
    </Box>
  );
}
