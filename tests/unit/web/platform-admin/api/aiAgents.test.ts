/**
 * Unit tests for AI Agents API client
 *
 * Tests API client methods with mocked responses.
 * Story 9.12c - AI Agent & Prompt Viewer UI
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../../../../../web/platform-admin/src/api/client';
import {
  listAiAgents,
  getAiAgent,
  listPromptsByAgent,
} from '../../../../../web/platform-admin/src/api/aiAgents';
import type {
  AgentConfigListResponse,
  AgentConfigDetail,
  PromptListResponse,
} from '../../../../../web/platform-admin/src/types/agent-config';

// Mock the API client
vi.mock('../../../../../web/platform-admin/src/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

describe('AI Agents API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('listAiAgents', () => {
    it('should fetch AI agents list with pagination', async () => {
      const mockResponse: AgentConfigListResponse = {
        data: [
          {
            agent_id: 'qc-event-extractor',
            version: '1.0.0',
            agent_type: 'extractor',
            status: 'active',
            description: 'Extracts QC event data',
            model: 'anthropic/claude-3-haiku',
            prompt_count: 1,
            updated_at: '2026-01-28T00:00:00Z',
          },
          {
            agent_id: 'disease-diagnosis',
            version: '1.0.0',
            agent_type: 'explorer',
            status: 'active',
            description: 'Diagnoses tea plant diseases',
            model: 'anthropic/claude-3-5-sonnet',
            prompt_count: 1,
            updated_at: '2026-01-28T00:00:00Z',
          },
        ],
        pagination: {
          total_count: 2,
          page_size: 25,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listAiAgents({ page_size: 25 });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/ai-agents', { page_size: 25 });
      expect(result.data).toHaveLength(2);
      expect(result.data[0].agent_type).toBe('extractor');
      expect(result.data[1].agent_type).toBe('explorer');
    });

    it('should filter by agent_type', async () => {
      const mockResponse: AgentConfigListResponse = {
        data: [
          {
            agent_id: 'qc-event-extractor',
            version: '1.0.0',
            agent_type: 'extractor',
            status: 'active',
            description: 'Extracts QC event data',
            model: 'anthropic/claude-3-haiku',
            prompt_count: 1,
            updated_at: '2026-01-28T00:00:00Z',
          },
        ],
        pagination: {
          total_count: 1,
          page_size: 25,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listAiAgents({ agent_type: 'extractor' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/ai-agents', {
        agent_type: 'extractor',
      });
    });

    it('should filter by status', async () => {
      const mockResponse: AgentConfigListResponse = {
        data: [
          {
            agent_id: 'disease-diagnosis',
            version: '1.0.0',
            agent_type: 'explorer',
            status: 'active',
            description: 'Diagnoses tea plant diseases',
            model: 'anthropic/claude-3-5-sonnet',
            prompt_count: 1,
            updated_at: '2026-01-28T00:00:00Z',
          },
        ],
        pagination: {
          total_count: 1,
          page_size: 25,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listAiAgents({ status: 'active' });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/ai-agents', {
        status: 'active',
      });
    });

    it('should handle empty results', async () => {
      const mockResponse: AgentConfigListResponse = {
        data: [],
        pagination: {
          total_count: 0,
          page_size: 25,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listAiAgents();

      expect(result.data).toHaveLength(0);
      expect(result.pagination.total_count).toBe(0);
    });

    it('should handle combined filters', async () => {
      const mockResponse: AgentConfigListResponse = {
        data: [],
        pagination: {
          total_count: 0,
          page_size: 10,
          next_page_token: null,
        },
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listAiAgents({ agent_type: 'generator', status: 'staged', page_size: 10 });

      expect(apiClient.get).toHaveBeenCalledWith('/admin/ai-agents', {
        agent_type: 'generator',
        status: 'staged',
        page_size: 10,
      });
    });
  });

  describe('getAiAgent', () => {
    it('should fetch extractor agent detail with config_json and prompts', async () => {
      const mockDetail: AgentConfigDetail = {
        agent_id: 'qc-event-extractor',
        version: '1.0.0',
        agent_type: 'extractor',
        status: 'active',
        description: 'Extracts QC event data from Starfish',
        model: 'anthropic/claude-3-haiku',
        prompt_count: 1,
        updated_at: '2026-01-28T00:00:00Z',
        created_at: '2026-01-09T00:00:00Z',
        config_json: JSON.stringify({
          agent_id: 'qc-event-extractor',
          version: '1.0.0',
          type: 'extractor',
          status: 'active',
          description: 'Extracts QC event data from Starfish',
          llm: {
            model: 'anthropic/claude-3-haiku',
            temperature: 0.1,
            max_tokens: 500,
          },
          extraction_schema: {
            required_fields: ['grade', 'quality_score'],
            optional_fields: ['farmer_id', 'defects'],
          },
        }),
        prompts: [
          {
            id: 'qc-event-extractor:1.0.0',
            prompt_id: 'qc-event-extractor',
            agent_id: 'qc-event-extractor',
            version: '1.0.0',
            status: 'active',
            author: 'dev-story-workflow',
            updated_at: '2026-01-09T00:00:00Z',
          },
        ],
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockDetail });

      const result = await getAiAgent('qc-event-extractor');

      expect(apiClient.get).toHaveBeenCalledWith('/admin/ai-agents/qc-event-extractor');
      expect(result.agent_id).toBe('qc-event-extractor');
      expect(result.agent_type).toBe('extractor');
      expect(result.prompts).toHaveLength(1);
      expect(result.config_json).toBeDefined();

      // Verify config_json can be parsed
      const parsedConfig = JSON.parse(result.config_json);
      expect(parsedConfig.llm.model).toBe('anthropic/claude-3-haiku');
      expect(parsedConfig.extraction_schema.required_fields).toContain('grade');
    });

    it('should fetch explorer agent with RAG config', async () => {
      const mockDetail: AgentConfigDetail = {
        agent_id: 'disease-diagnosis',
        version: '1.0.0',
        agent_type: 'explorer',
        status: 'active',
        description: 'Diagnoses tea plant diseases',
        model: 'anthropic/claude-3-5-sonnet',
        prompt_count: 1,
        updated_at: '2026-01-28T00:00:00Z',
        created_at: '2026-01-28T00:00:00Z',
        config_json: JSON.stringify({
          agent_id: 'disease-diagnosis',
          version: '1.0.0',
          type: 'explorer',
          status: 'active',
          description: 'Diagnoses tea plant diseases',
          llm: {
            model: 'anthropic/claude-3-5-sonnet',
            temperature: 0.3,
            max_tokens: 2000,
          },
          rag: {
            enabled: true,
            knowledge_domains: ['plant_diseases', 'tea_cultivation'],
            top_k: 5,
            min_similarity: 0.7,
          },
        }),
        prompts: [
          {
            id: 'disease-diagnosis:1.0.0',
            prompt_id: 'disease-diagnosis',
            agent_id: 'disease-diagnosis',
            version: '1.0.0',
            status: 'active',
            author: 'dev-story-9.12a',
            updated_at: '2026-01-28T00:00:00Z',
          },
        ],
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockDetail });

      const result = await getAiAgent('disease-diagnosis');

      expect(result.agent_type).toBe('explorer');

      const parsedConfig = JSON.parse(result.config_json);
      expect(parsedConfig.rag.enabled).toBe(true);
      expect(parsedConfig.rag.knowledge_domains).toContain('plant_diseases');
    });

    it('should URL-encode agent_id with special characters', async () => {
      const mockDetail: AgentConfigDetail = {
        agent_id: 'test-agent:special',
        version: '1.0.0',
        agent_type: 'generator',
        status: 'draft',
        description: 'Test agent',
        model: 'test',
        prompt_count: 0,
        updated_at: null,
        created_at: null,
        config_json: '{}',
        prompts: [],
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockDetail });

      await getAiAgent('test-agent:special');

      expect(apiClient.get).toHaveBeenCalledWith('/admin/ai-agents/test-agent%3Aspecial');
    });
  });

  describe('listPromptsByAgent', () => {
    it('should fetch prompts for an agent', async () => {
      const mockResponse: PromptListResponse = {
        data: [
          {
            id: 'qc-event-extractor:1.0.0',
            prompt_id: 'qc-event-extractor',
            agent_id: 'qc-event-extractor',
            version: '1.0.0',
            status: 'active',
            author: 'dev-story-workflow',
            updated_at: '2026-01-09T00:00:00Z',
          },
        ],
        total_count: 1,
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listPromptsByAgent('qc-event-extractor');

      expect(apiClient.get).toHaveBeenCalledWith(
        '/admin/ai-agents/qc-event-extractor/prompts',
        {}
      );
      expect(result.data).toHaveLength(1);
      expect(result.data[0].status).toBe('active');
    });

    it('should filter prompts by status', async () => {
      const mockResponse: PromptListResponse = {
        data: [
          {
            id: 'disease-diagnosis:2.0.0',
            prompt_id: 'disease-diagnosis',
            agent_id: 'disease-diagnosis',
            version: '2.0.0',
            status: 'archived',
            author: 'jlt',
            updated_at: '2026-01-15T00:00:00Z',
          },
        ],
        total_count: 1,
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listPromptsByAgent('disease-diagnosis', 'archived');

      expect(apiClient.get).toHaveBeenCalledWith(
        '/admin/ai-agents/disease-diagnosis/prompts',
        { status: 'archived' }
      );
    });

    it('should handle agent with no prompts', async () => {
      const mockResponse: PromptListResponse = {
        data: [],
        total_count: 0,
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listPromptsByAgent('new-agent');

      expect(result.data).toHaveLength(0);
      expect(result.total_count).toBe(0);
    });

    it('should URL-encode agent_id with special characters', async () => {
      const mockResponse: PromptListResponse = {
        data: [],
        total_count: 0,
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await listPromptsByAgent('test:agent/name');

      expect(apiClient.get).toHaveBeenCalledWith(
        '/admin/ai-agents/test%3Aagent%2Fname/prompts',
        {}
      );
    });
  });

  describe('Error handling', () => {
    it('should throw error on API failure', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      await expect(listAiAgents()).rejects.toThrow('Network error');
    });

    it('should throw error on 404 response', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Agent config not found'));

      await expect(getAiAgent('nonexistent')).rejects.toThrow('Agent config not found');
    });

    it('should throw error on unauthorized access', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Unauthorized'));

      await expect(listAiAgents()).rejects.toThrow('Unauthorized');
    });

    it('should throw 503 error when AI Model service unavailable', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Service unavailable'));

      await expect(listAiAgents()).rejects.toThrow('Service unavailable');
    });
  });
});
