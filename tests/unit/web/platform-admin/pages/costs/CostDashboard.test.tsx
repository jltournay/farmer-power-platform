/**
 * Unit tests for CostDashboard and tab components
 *
 * Story 9.10b - Platform Cost Dashboard UI
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { CostDashboard } from '../../../../../../web/platform-admin/src/pages/costs/CostDashboard';
import { MetricCard } from '../../../../../../web/platform-admin/src/pages/costs/components/MetricCard';
import { BudgetBar } from '../../../../../../web/platform-admin/src/pages/costs/components/BudgetBar';
import { DateRangePicker } from '../../../../../../web/platform-admin/src/pages/costs/components/DateRangePicker';
import { ExportButton } from '../../../../../../web/platform-admin/src/pages/costs/components/ExportButton';
import { BudgetConfigDialog } from '../../../../../../web/platform-admin/src/pages/costs/components/BudgetConfigDialog';
import type { BudgetStatusResponse } from '../../../../../../web/platform-admin/src/api/types';

// Mock all API calls
vi.mock('../../../../../../web/platform-admin/src/api/costs', () => ({
  getCostSummary: vi.fn().mockResolvedValue({
    total_cost_usd: '1892.30',
    total_requests: 3386,
    by_type: [
      { cost_type: 'llm', total_cost_usd: '1195.50', total_quantity: 0, request_count: 2340, percentage: 63 },
    ],
    period_start: '2025-12-25',
    period_end: '2026-01-24',
  }),
  getDailyTrend: vi.fn().mockResolvedValue({
    entries: [
      { entry_date: '2026-01-22', total_cost_usd: '65.40', llm_cost_usd: '45.20', document_cost_usd: '12.80', embedding_cost_usd: '7.40' },
    ],
    data_available_from: '2025-11-01',
  }),
  getCurrentDayCost: vi.fn().mockResolvedValue({
    cost_date: '2026-01-24',
    total_cost_usd: '66.40',
    by_type: { llm: '45.20', document: '12.80', embedding: '8.40' },
    updated_at: '2026-01-24T14:32:00Z',
  }),
  getBudgetStatus: vi.fn().mockResolvedValue({
    daily_threshold_usd: '150.00',
    daily_total_usd: '66.40',
    daily_remaining_usd: '83.60',
    daily_utilization_percent: 44.3,
    monthly_threshold_usd: '4000.00',
    monthly_total_usd: '1892.30',
    monthly_remaining_usd: '2107.70',
    monthly_utilization_percent: 47.3,
    by_type: { llm: '45.20' },
    current_day: '2026-01-24',
    current_month: '2026-01',
  }),
  getLlmByAgentType: vi.fn().mockResolvedValue({
    agent_costs: [{ agent_type: 'explorer', cost_usd: '538.00', request_count: 1053, tokens_in: 2106000, tokens_out: 890000, percentage: 45 }],
    total_llm_cost_usd: '1195.50',
  }),
  getLlmByModel: vi.fn().mockResolvedValue({
    model_costs: [{ model: 'claude-3-haiku', cost_usd: '717.00', request_count: 1400, tokens_in: 2800000, tokens_out: 1100000, percentage: 60 }],
    total_llm_cost_usd: '1195.50',
  }),
  getDocumentCosts: vi.fn().mockResolvedValue({
    total_cost_usd: '412.30',
    total_pages: 1240,
    avg_cost_per_page_usd: '0.33',
    document_count: 156,
    period_start: '2025-12-25',
    period_end: '2026-01-24',
  }),
  getEmbeddingsByDomain: vi.fn().mockResolvedValue({
    domain_costs: [{ knowledge_domain: 'tea-quality', cost_usd: '119.00', tokens_total: 1340000, texts_count: 1890, percentage: 42 }],
    total_embedding_cost_usd: '284.50',
  }),
  configureBudget: vi.fn().mockResolvedValue({
    daily_threshold_usd: '200.00',
    monthly_threshold_usd: '5000.00',
    message: 'Updated',
    updated_at: '2026-01-24T15:00:00Z',
  }),
}));

// Mock ResizeObserver for Recharts
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverMock;

describe('CostDashboard', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders page title "Platform Costs"', async () => {
    await act(async () => {
      render(<CostDashboard />);
    });
    expect(screen.getByText('Platform Costs')).toBeInTheDocument();
  });

  it('renders all four tabs', async () => {
    await act(async () => {
      render(<CostDashboard />);
    });
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'LLM' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Documents' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Embeddings' })).toBeInTheDocument();
  });

  it('renders Budget button', async () => {
    await act(async () => {
      render(<CostDashboard />);
    });
    expect(screen.getByText('Budget')).toBeInTheDocument();
  });

  it('switches to LLM tab on click', async () => {
    vi.useRealTimers();
    await act(async () => {
      render(<CostDashboard />);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'LLM' }));
    });
    await waitFor(() => {
      expect(screen.getByText('Cost by Agent Type')).toBeInTheDocument();
    });
  });

  it('switches to Documents tab on click', async () => {
    vi.useRealTimers();
    await act(async () => {
      render(<CostDashboard />);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Documents' }));
    });
    await waitFor(() => {
      expect(screen.getByText('Pages Processed')).toBeInTheDocument();
    });
  });

  it('switches to Embeddings tab on click', async () => {
    vi.useRealTimers();
    await act(async () => {
      render(<CostDashboard />);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('tab', { name: 'Embeddings' }));
    });
    await waitFor(() => {
      expect(screen.getByText('Cost by Knowledge Domain')).toBeInTheDocument();
    });
  });
});

describe('MetricCard', () => {
  it('renders label and value', () => {
    render(<MetricCard label="Total Cost" value="$1,892.30" />);
    expect(screen.getByText('Total Cost')).toBeInTheDocument();
    expect(screen.getByText('$1,892.30')).toBeInTheDocument();
  });

  it('renders subtitle when provided', () => {
    render(<MetricCard label="Total Cost" value="$1,892.30" subtitle="3,386 requests" />);
    expect(screen.getByText('3,386 requests')).toBeInTheDocument();
  });

  it('renders skeleton when loading', () => {
    const { container } = render(<MetricCard label="Total Cost" value="$0" loading />);
    expect(container.querySelectorAll('.MuiSkeleton-root').length).toBeGreaterThan(0);
  });
});

describe('BudgetBar', () => {
  it('renders label and utilization', () => {
    render(<BudgetBar label="Daily" utilization={44} current="66.40" threshold="150.00" />);
    expect(screen.getByText('Daily')).toBeInTheDocument();
    expect(screen.getByText('44%')).toBeInTheDocument();
  });

  it('renders skeleton when loading', () => {
    const { container } = render(<BudgetBar label="Daily" utilization={0} current="0" threshold="0" loading />);
    expect(container.querySelectorAll('.MuiSkeleton-root').length).toBeGreaterThan(0);
  });

  it('displays current/threshold text', () => {
    render(<BudgetBar label="Monthly" utilization={47} current="1892.30" threshold="4000.00" />);
    expect(screen.getByText('$1892.30 / $4000.00')).toBeInTheDocument();
  });
});

describe('DateRangePicker', () => {
  it('renders preset buttons', () => {
    render(
      <DateRangePicker
        startDate="2026-01-01"
        endDate="2026-01-24"
        onStartDateChange={() => {}}
        onEndDateChange={() => {}}
      />
    );
    expect(screen.getByText('7d')).toBeInTheDocument();
    expect(screen.getByText('14d')).toBeInTheDocument();
    expect(screen.getByText('30d')).toBeInTheDocument();
    expect(screen.getByText('90d')).toBeInTheDocument();
  });

  it('calls onStartDateChange and onEndDateChange when preset clicked', () => {
    const onStart = vi.fn();
    const onEnd = vi.fn();
    render(
      <DateRangePicker
        startDate="2026-01-01"
        endDate="2026-01-24"
        onStartDateChange={onStart}
        onEndDateChange={onEnd}
      />
    );
    fireEvent.click(screen.getByText('7d'));
    expect(onStart).toHaveBeenCalled();
    expect(onEnd).toHaveBeenCalled();
  });
});

describe('ExportButton', () => {
  it('is disabled when data is empty', () => {
    render(<ExportButton data={[]} filename="test.csv" />);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('is enabled when data has entries', () => {
    render(<ExportButton data={[{ col: 'val' }]} filename="test.csv" />);
    const button = screen.getByRole('button');
    expect(button).not.toBeDisabled();
  });

  it('triggers download on click', () => {
    const createObjectURL = vi.fn(() => 'blob:url');
    const revokeObjectURL = vi.fn();
    Object.defineProperty(window.URL, 'createObjectURL', { value: createObjectURL });
    Object.defineProperty(window.URL, 'revokeObjectURL', { value: revokeObjectURL });

    render(<ExportButton data={[{ name: 'test', cost: '10.00' }]} filename="export.csv" />);
    fireEvent.click(screen.getByRole('button'));

    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalled();
  });
});

describe('BudgetConfigDialog', () => {
  const mockBudgetStatus: BudgetStatusResponse = {
    daily_threshold_usd: '150.00',
    daily_total_usd: '66.40',
    daily_remaining_usd: '83.60',
    daily_utilization_percent: 44.3,
    monthly_threshold_usd: '4000.00',
    monthly_total_usd: '1892.30',
    monthly_remaining_usd: '2107.70',
    monthly_utilization_percent: 47.3,
    by_type: {},
    current_day: '2026-01-24',
    current_month: '2026-01',
  };

  it('renders dialog when open', () => {
    render(
      <BudgetConfigDialog
        open={true}
        onClose={() => {}}
        budgetStatus={mockBudgetStatus}
        onSuccess={() => {}}
      />
    );
    expect(screen.getByText('Configure Budget Thresholds')).toBeInTheDocument();
  });

  it('has Save and Cancel buttons', () => {
    render(
      <BudgetConfigDialog
        open={true}
        onClose={() => {}}
        budgetStatus={mockBudgetStatus}
        onSuccess={() => {}}
      />
    );
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Save Thresholds')).toBeInTheDocument();
  });

  it('calls onClose when Cancel clicked', () => {
    const onClose = vi.fn();
    render(
      <BudgetConfigDialog
        open={true}
        onClose={onClose}
        budgetStatus={mockBudgetStatus}
        onSuccess={() => {}}
      />
    );
    fireEvent.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalled();
  });
});
