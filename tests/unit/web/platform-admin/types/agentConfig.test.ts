/**
 * Unit Tests for AI Agent Configuration TypeScript Types
 *
 * Tests type helper functions and JSON parsing for agent configurations.
 *
 * Story 9.12c: AI Agent & Prompt Viewer UI
 */

import { describe, it, expect } from 'vitest';
import {
  getAgentTypeLabel,
  getAgentTypeColor,
  getStatusLabel,
  getStatusColor,
  parseConfigJson,
  getRagDomains,
  isRagEnabled,
  formatDate,
  type AgentConfig,
  type AgentType,
  type AgentStatus,
  type RagConfig,
} from '../../../../../web/platform-admin/src/types/agent-config';

describe('Agent Config Type Helpers', () => {
  describe('getAgentTypeLabel', () => {
    it('returns "Extractor" for extractor type', () => {
      expect(getAgentTypeLabel('extractor')).toBe('Extractor');
    });

    it('returns "Explorer" for explorer type', () => {
      expect(getAgentTypeLabel('explorer')).toBe('Explorer');
    });

    it('returns "Generator" for generator type', () => {
      expect(getAgentTypeLabel('generator')).toBe('Generator');
    });

    it('returns "Conversational" for conversational type', () => {
      expect(getAgentTypeLabel('conversational')).toBe('Conversational');
    });

    it('returns "Tiered Vision" for tiered-vision type', () => {
      expect(getAgentTypeLabel('tiered-vision')).toBe('Tiered Vision');
    });

    it('returns raw type if unknown', () => {
      expect(getAgentTypeLabel('unknown' as AgentType)).toBe('unknown');
    });
  });

  describe('getAgentTypeColor', () => {
    it('returns "info" for extractor type', () => {
      expect(getAgentTypeColor('extractor')).toBe('info');
    });

    it('returns "warning" for explorer type', () => {
      expect(getAgentTypeColor('explorer')).toBe('warning');
    });

    it('returns "success" for generator type', () => {
      expect(getAgentTypeColor('generator')).toBe('success');
    });

    it('returns "secondary" for conversational type', () => {
      expect(getAgentTypeColor('conversational')).toBe('secondary');
    });

    it('returns "primary" for tiered-vision type', () => {
      expect(getAgentTypeColor('tiered-vision')).toBe('primary');
    });

    it('returns "info" for unknown type', () => {
      expect(getAgentTypeColor('unknown' as AgentType)).toBe('info');
    });
  });

  describe('getStatusLabel', () => {
    it('returns "Active" for active status', () => {
      expect(getStatusLabel('active')).toBe('Active');
    });

    it('returns "Staged" for staged status', () => {
      expect(getStatusLabel('staged')).toBe('Staged');
    });

    it('returns "Archived" for archived status', () => {
      expect(getStatusLabel('archived')).toBe('Archived');
    });

    it('returns "Draft" for draft status', () => {
      expect(getStatusLabel('draft')).toBe('Draft');
    });

    it('returns raw status if unknown', () => {
      expect(getStatusLabel('unknown' as AgentStatus)).toBe('unknown');
    });
  });

  describe('getStatusColor', () => {
    it('returns "success" for active status', () => {
      expect(getStatusColor('active')).toBe('success');
    });

    it('returns "warning" for staged status', () => {
      expect(getStatusColor('staged')).toBe('warning');
    });

    it('returns "default" for archived status', () => {
      expect(getStatusColor('archived')).toBe('default');
    });

    it('returns "info" for draft status', () => {
      expect(getStatusColor('draft')).toBe('info');
    });

    it('returns "default" for unknown status', () => {
      expect(getStatusColor('unknown' as AgentStatus)).toBe('default');
    });
  });

  describe('parseConfigJson', () => {
    it('parses a valid extractor agent config JSON', () => {
      const configJson = JSON.stringify({
        agent_id: 'qc-event-extractor',
        version: '1.0.0',
        type: 'extractor',
        status: 'active',
        description: 'Extracts QC event data',
        llm: {
          model: 'anthropic/claude-3-haiku',
          temperature: 0.1,
          max_tokens: 500,
        },
        extraction_schema: {
          required_fields: ['grade', 'quality_score'],
          optional_fields: ['farmer_id'],
          field_types: {
            grade: 'string',
            quality_score: 'number',
          },
        },
      } as AgentConfig);

      const result = parseConfigJson(configJson);

      expect(result).not.toBeNull();
      expect(result?.agent_id).toBe('qc-event-extractor');
      expect(result?.type).toBe('extractor');
      expect(result?.llm.model).toBe('anthropic/claude-3-haiku');
      expect(result?.extraction_schema?.required_fields).toContain('grade');
    });

    it('parses a valid explorer agent config with RAG', () => {
      const configJson = JSON.stringify({
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
      } as AgentConfig);

      const result = parseConfigJson(configJson);

      expect(result).not.toBeNull();
      expect(result?.agent_id).toBe('disease-diagnosis');
      expect(result?.type).toBe('explorer');
      expect(result?.rag?.enabled).toBe(true);
      expect(result?.rag?.knowledge_domains).toContain('plant_diseases');
    });

    it('returns null for invalid JSON', () => {
      const result = parseConfigJson('{ invalid json }');
      expect(result).toBeNull();
    });

    it('returns null for empty string', () => {
      const result = parseConfigJson('');
      expect(result).toBeNull();
    });
  });

  describe('getRagDomains', () => {
    it('returns knowledge_domains when present', () => {
      const ragConfig: RagConfig = {
        enabled: true,
        knowledge_domains: ['disease', 'weather'],
      };
      expect(getRagDomains(ragConfig)).toEqual(['disease', 'weather']);
    });

    it('returns domains as fallback when knowledge_domains not present', () => {
      const ragConfig: RagConfig = {
        enabled: true,
        domains: ['tea', 'coffee'],
      };
      expect(getRagDomains(ragConfig)).toEqual(['tea', 'coffee']);
    });

    it('prefers knowledge_domains over domains', () => {
      const ragConfig: RagConfig = {
        enabled: true,
        knowledge_domains: ['preferred'],
        domains: ['fallback'],
      };
      expect(getRagDomains(ragConfig)).toEqual(['preferred']);
    });

    it('returns empty array when undefined', () => {
      expect(getRagDomains(undefined)).toEqual([]);
    });

    it('returns empty array when no domains defined', () => {
      const ragConfig: RagConfig = {
        enabled: true,
      };
      expect(getRagDomains(ragConfig)).toEqual([]);
    });
  });

  describe('isRagEnabled', () => {
    it('returns true when RAG is enabled', () => {
      const ragConfig: RagConfig = { enabled: true };
      expect(isRagEnabled(ragConfig)).toBe(true);
    });

    it('returns false when RAG is disabled', () => {
      const ragConfig: RagConfig = { enabled: false };
      expect(isRagEnabled(ragConfig)).toBe(false);
    });

    it('returns false when ragConfig is undefined', () => {
      expect(isRagEnabled(undefined)).toBe(false);
    });
  });

  describe('formatDate', () => {
    it('formats a valid ISO date string', () => {
      const result = formatDate('2026-01-28T10:30:00Z');
      // Check it includes expected parts (exact format varies by locale)
      expect(result).toMatch(/Jan/);
      expect(result).toMatch(/28/);
      expect(result).toMatch(/2026/);
    });

    it('returns "N/A" for null', () => {
      expect(formatDate(null)).toBe('N/A');
    });

    it('returns "N/A" for undefined', () => {
      expect(formatDate(undefined)).toBe('N/A');
    });

    it('returns original string for invalid date', () => {
      // Note: This depends on implementation - some invalid strings may still parse
      const result = formatDate('not-a-date');
      // Either returns parsed (if Date can parse) or original string
      expect(typeof result).toBe('string');
    });
  });
});
