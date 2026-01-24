/**
 * Unit tests for Cost API client
 *
 * Tests API client methods with mocked responses.
 * Story 9.10b - Platform Cost Dashboard UI
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import apiClient from '../../../../../web/platform-admin/src/api/client';
import {
  getCostSummary,
  getDailyTrend,
  getCurrentDayCost,
  getLlmByAgentType,
  getLlmByModel,
  getDocumentCosts,
  getEmbeddingsByDomain,
  getBudgetStatus,
  configureBudget,
} from '../../../../../web/platform-admin/src/api/costs';
import type {
  CostSummaryResponse,
  DailyTrendResponse,
  CurrentDayCostResponse,
  LlmByAgentTypeResponse,
  LlmByModelResponse,
  DocumentCostResponse,
  EmbeddingByDomainResponse,
  BudgetStatusResponse,
  BudgetConfigResponse,
} from '../../../../../web/platform-admin/src/api/types';

// Mock the API client
vi.mock('../../../../../web/platform-admin/src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockSummary: CostSummaryResponse = {
  total_cost_usd: '1892.30',
  total_requests: 3386,
  by_type: [
    { cost_type: 'llm', total_cost_usd: '1195.50', total_quantity: 0, request_count: 2340, percentage: 63 },
    { cost_type: 'document', total_cost_usd: '412.30', total_quantity: 1240, request_count: 156, percentage: 22 },
    { cost_type: 'embedding', total_cost_usd: '284.50', total_quantity: 45200, request_count: 890, percentage: 15 },
  ],
  period_start: '2025-12-25',
  period_end: '2026-01-24',
};

const mockTrend: DailyTrendResponse = {
  entries: [
    { entry_date: '2026-01-22', total_cost_usd: '65.40', llm_cost_usd: '45.20', document_cost_usd: '12.80', embedding_cost_usd: '7.40' },
    { entry_date: '2026-01-23', total_cost_usd: '72.10', llm_cost_usd: '50.00', document_cost_usd: '14.00', embedding_cost_usd: '8.10' },
  ],
  data_available_from: '2025-11-01',
};

const mockToday: CurrentDayCostResponse = {
  cost_date: '2026-01-24',
  total_cost_usd: '66.40',
  by_type: { llm: '45.20', document: '12.80', embedding: '8.40' },
  updated_at: '2026-01-24T14:32:00Z',
};

const mockAgentType: LlmByAgentTypeResponse = {
  agent_costs: [
    { agent_type: 'explorer', cost_usd: '538.00', request_count: 1053, tokens_in: 2106000, tokens_out: 890000, percentage: 45 },
    { agent_type: 'generator', cost_usd: '358.00', request_count: 745, tokens_in: 1490000, tokens_out: 620000, percentage: 30 },
  ],
  total_llm_cost_usd: '1195.50',
};

const mockByModel: LlmByModelResponse = {
  model_costs: [
    { model: 'anthropic/claude-3-haiku', cost_usd: '717.00', request_count: 1400, tokens_in: 2800000, tokens_out: 1100000, percentage: 60 },
  ],
  total_llm_cost_usd: '1195.50',
};

const mockDocCost: DocumentCostResponse = {
  total_cost_usd: '412.30',
  total_pages: 1240,
  avg_cost_per_page_usd: '0.33',
  document_count: 156,
  period_start: '2025-12-25',
  period_end: '2026-01-24',
};

const mockEmbedding: EmbeddingByDomainResponse = {
  domain_costs: [
    { knowledge_domain: 'tea-quality', cost_usd: '119.00', tokens_total: 1340000, texts_count: 1890, percentage: 42 },
  ],
  total_embedding_cost_usd: '284.50',
};

const mockBudget: BudgetStatusResponse = {
  daily_threshold_usd: '150.00',
  daily_total_usd: '66.40',
  daily_remaining_usd: '83.60',
  daily_utilization_percent: 44.3,
  monthly_threshold_usd: '4000.00',
  monthly_total_usd: '1892.30',
  monthly_remaining_usd: '2107.70',
  monthly_utilization_percent: 47.3,
  by_type: { llm: '45.20', document: '12.80', embedding: '8.40' },
  current_day: '2026-01-24',
  current_month: '2026-01',
};

const mockBudgetConfig: BudgetConfigResponse = {
  daily_threshold_usd: '200.00',
  monthly_threshold_usd: '5000.00',
  message: 'Budget thresholds updated',
  updated_at: '2026-01-24T15:00:00Z',
};

describe('Cost API Module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getCostSummary', () => {
    it('calls /admin/costs/summary with date params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockSummary });

      const result = await getCostSummary({ start_date: '2025-12-25', end_date: '2026-01-24' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/summary', {
        start_date: '2025-12-25',
        end_date: '2026-01-24',
      });
      expect(result.total_cost_usd).toBe('1892.30');
      expect(result.by_type).toHaveLength(3);
    });

    it('calls without params when none provided', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockSummary });

      await getCostSummary();

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/summary', {});
    });
  });

  describe('getDailyTrend', () => {
    it('calls /admin/costs/trend/daily with days param', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockTrend });

      const result = await getDailyTrend(30);

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/trend/daily', { days: 30 });
      expect(result.entries).toHaveLength(2);
    });

    it('calls without days when not provided', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockTrend });

      await getDailyTrend();

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/trend/daily', {});
    });
  });

  describe('getCurrentDayCost', () => {
    it('calls /admin/costs/today without params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockToday });

      const result = await getCurrentDayCost();

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/today');
      expect(result.total_cost_usd).toBe('66.40');
      expect(result.by_type).toHaveProperty('llm');
    });
  });

  describe('getLlmByAgentType', () => {
    it('calls /admin/costs/llm/by-agent-type with date range', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockAgentType });

      const result = await getLlmByAgentType({ start_date: '2025-12-25', end_date: '2026-01-24' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/llm/by-agent-type', {
        start_date: '2025-12-25',
        end_date: '2026-01-24',
      });
      expect(result.agent_costs).toHaveLength(2);
      expect(result.total_llm_cost_usd).toBe('1195.50');
    });
  });

  describe('getLlmByModel', () => {
    it('calls /admin/costs/llm/by-model', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockByModel });

      const result = await getLlmByModel({ start_date: '2025-12-25', end_date: '2026-01-24' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/llm/by-model', {
        start_date: '2025-12-25',
        end_date: '2026-01-24',
      });
      expect(result.model_costs[0].model).toBe('anthropic/claude-3-haiku');
    });
  });

  describe('getDocumentCosts', () => {
    it('calls /admin/costs/documents with date range', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockDocCost });

      const result = await getDocumentCosts({ start_date: '2025-12-25', end_date: '2026-01-24' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/documents', {
        start_date: '2025-12-25',
        end_date: '2026-01-24',
      });
      expect(result.total_pages).toBe(1240);
    });
  });

  describe('getEmbeddingsByDomain', () => {
    it('calls /admin/costs/embeddings/by-domain', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockEmbedding });

      const result = await getEmbeddingsByDomain({ start_date: '2025-12-25', end_date: '2026-01-24' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/embeddings/by-domain', {
        start_date: '2025-12-25',
        end_date: '2026-01-24',
      });
      expect(result.domain_costs[0].knowledge_domain).toBe('tea-quality');
    });
  });

  describe('getBudgetStatus', () => {
    it('calls /admin/costs/budget', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockBudget });

      const result = await getBudgetStatus();

      expect(apiClient.get).toHaveBeenCalledWith('/admin/costs/budget');
      expect(result.daily_threshold_usd).toBe('150.00');
      expect(result.monthly_utilization_percent).toBe(47.3);
    });
  });

  describe('configureBudget', () => {
    it('calls PUT /admin/costs/budget with thresholds', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: mockBudgetConfig });

      const result = await configureBudget({
        daily_threshold_usd: '200.00',
        monthly_threshold_usd: '5000.00',
      });

      expect(apiClient.put).toHaveBeenCalledWith('/admin/costs/budget', {
        daily_threshold_usd: '200.00',
        monthly_threshold_usd: '5000.00',
      });
      expect(result.message).toBe('Budget thresholds updated');
    });
  });
});
