/**
 * Unit Tests for SourceConfigList Page Component
 *
 * Tests the Source Configuration list page with filtering, pagination,
 * and detail panel opening functionality.
 * Story 9.11c - Source Configuration Viewer UI
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { SourceConfigList } from '../../../../../../web/platform-admin/src/pages/source-configs/SourceConfigList';
import * as api from '../../../../../../web/platform-admin/src/api/sourceConfigs';
import type {
  SourceConfigListResponse,
  SourceConfigDetailResponse,
} from '../../../../../../web/platform-admin/src/types/source-config';

// Mock the API module
vi.mock('../../../../../../web/platform-admin/src/api/sourceConfigs', () => ({
  listSourceConfigs: vi.fn(),
  getSourceConfig: vi.fn(),
}));

// Mock @fp/ui-components
vi.mock('@fp/ui-components', () => ({
  PageHeader: ({ title, subtitle }: { title: string; subtitle?: string }) => (
    <div data-testid="page-header">
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
  ),
  DataTable: ({
    columns,
    rows,
    loading,
    onRowClick,
    noRowsText,
  }: {
    columns: unknown[];
    rows: unknown[];
    loading?: boolean;
    onRowClick?: (row: unknown) => void;
    noRowsText?: string;
  }) => (
    <div data-testid="data-table">
      {loading && <div data-testid="table-loading">Loading...</div>}
      {rows.length === 0 && !loading && <div data-testid="no-rows">{noRowsText}</div>}
      {rows.map((row: Record<string, unknown>, idx: number) => (
        <div
          key={idx}
          data-testid={`row-${row.source_id}`}
          onClick={() => onRowClick?.(row)}
        >
          {row.display_name as string}
        </div>
      ))}
    </div>
  ),
  FilterBar: ({
    onFilterChange,
    onSearchChange,
  }: {
    onFilterChange: (id: string, value: string) => void;
    onSearchChange?: (value: string) => void;
  }) => (
    <div data-testid="filter-bar">
      <select
        data-testid="filter-enabled"
        onChange={(e) => onFilterChange('enabled_only', e.target.value)}
      >
        <option value="">All</option>
        <option value="true">Enabled Only</option>
      </select>
      <select
        data-testid="filter-mode"
        onChange={(e) => onFilterChange('ingestion_mode', e.target.value)}
      >
        <option value="">All</option>
        <option value="blob_trigger">Blob Trigger</option>
        <option value="scheduled_pull">Scheduled Pull</option>
      </select>
      <input
        data-testid="search-input"
        onChange={(e) => onSearchChange?.(e.target.value)}
        placeholder="Search..."
      />
    </div>
  ),
}));

// Mock @fp/auth
vi.mock('@fp/auth', () => ({
  useAuth: () => ({
    user: { role: 'platform_admin' },
    isAuthenticated: true,
  }),
}));

// Test wrapper with router
const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('SourceConfigList', () => {
  const mockListResponse: SourceConfigListResponse = {
    data: [
      {
        source_id: 'qc-bag-result',
        display_name: 'QC Bag Results',
        description: 'Quality control results',
        enabled: true,
        ingestion_mode: 'blob_trigger',
        ai_agent_id: 'quality-extraction',
      },
      {
        source_id: 'weather-data',
        display_name: 'Weather Data',
        description: 'Regional weather observations',
        enabled: true,
        ingestion_mode: 'scheduled_pull',
        ai_agent_id: '',
      },
      {
        source_id: 'legacy-source',
        display_name: 'Legacy Source',
        description: 'Deprecated source',
        enabled: false,
        ingestion_mode: 'blob_trigger',
        ai_agent_id: 'legacy-agent',
      },
    ],
    pagination: {
      total_count: 3,
      page_size: 25,
      next_page_token: null,
    },
  };

  const mockDetailResponse: SourceConfigDetailResponse = {
    source_id: 'qc-bag-result',
    display_name: 'QC Bag Results',
    description: 'Quality control results',
    enabled: true,
    ingestion_mode: 'blob_trigger',
    ai_agent_id: 'quality-extraction',
    config_json: JSON.stringify({
      source_id: 'qc-bag-result',
      display_name: 'QC Bag Results',
      description: 'Quality control results',
      enabled: true,
      ingestion: { mode: 'blob_trigger', landing_container: 'data-landing' },
      transformation: { ai_agent_id: 'quality-extraction', extract_fields: [], link_field: 'id', field_mappings: {} },
      storage: { raw_container: 'raw', index_collection: 'results' },
    }),
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSourceConfigs).mockResolvedValue(mockListResponse);
    vi.mocked(api.getSourceConfig).mockResolvedValue(mockDetailResponse);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('renders page header with correct title', async () => {
    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('page-header')).toBeInTheDocument();
    });
    expect(screen.getByText('Source Configurations')).toBeInTheDocument();
  });

  it('renders filter bar', async () => {
    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('filter-bar')).toBeInTheDocument();
    });
  });

  it('renders data table with source configs', async () => {
    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('data-table')).toBeInTheDocument();
    });

    expect(screen.getByText('QC Bag Results')).toBeInTheDocument();
    expect(screen.getByText('Weather Data')).toBeInTheDocument();
    expect(screen.getByText('Legacy Source')).toBeInTheDocument();
  });

  it('shows loading state initially', async () => {
    // Delay the API response to see loading state
    vi.mocked(api.listSourceConfigs).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockListResponse), 100))
    );

    renderWithRouter(<SourceConfigList />);

    // Should show loading spinner initially
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('QC Bag Results')).toBeInTheDocument();
    });
  });

  it('shows error state with retry button on API failure (AC 9.11c.5)', async () => {
    vi.mocked(api.listSourceConfigs).mockRejectedValue(new Error('Service unavailable'));

    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByText('Service unavailable')).toBeInTheDocument();
    });

    // Should have retry button (AC 9.11c.5)
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('retries fetch when retry button is clicked', async () => {
    vi.mocked(api.listSourceConfigs)
      .mockRejectedValueOnce(new Error('Service unavailable'))
      .mockResolvedValueOnce(mockListResponse);

    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByText('Service unavailable')).toBeInTheDocument();
    });

    // Click retry button
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));

    // Should call API again
    await waitFor(() => {
      expect(api.listSourceConfigs).toHaveBeenCalledTimes(2);
    });

    // Should show data after successful retry
    await waitFor(() => {
      expect(screen.getByText('QC Bag Results')).toBeInTheDocument();
    });
  });

  it('shows empty state when no configs exist (AC 9.11c.5)', async () => {
    vi.mocked(api.listSourceConfigs).mockResolvedValue({
      data: [],
      pagination: { total_count: 0, page_size: 25, next_page_token: null },
    });

    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('no-rows')).toBeInTheDocument();
    });
    expect(screen.getByText('No source configurations found')).toBeInTheDocument();
  });

  it('filters by enabled_only when filter is changed (AC 9.11c.4)', async () => {
    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('data-table')).toBeInTheDocument();
    });

    // Change enabled filter
    fireEvent.change(screen.getByTestId('filter-enabled'), { target: { value: 'true' } });

    // Should call API with enabled_only filter
    await waitFor(() => {
      expect(api.listSourceConfigs).toHaveBeenCalledWith(
        expect.objectContaining({ enabled_only: true })
      );
    });
  });

  it('filters by ingestion_mode when filter is changed (AC 9.11c.4)', async () => {
    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('data-table')).toBeInTheDocument();
    });

    // Change mode filter
    fireEvent.change(screen.getByTestId('filter-mode'), { target: { value: 'blob_trigger' } });

    // Should call API with ingestion_mode filter
    await waitFor(() => {
      expect(api.listSourceConfigs).toHaveBeenCalledWith(
        expect.objectContaining({ ingestion_mode: 'blob_trigger' })
      );
    });
  });

  it('opens detail drawer when row is clicked (AC 9.11c.1)', async () => {
    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('row-qc-bag-result')).toBeInTheDocument();
    });

    // Click on a row
    fireEvent.click(screen.getByTestId('row-qc-bag-result'));

    // Should fetch detail
    await waitFor(() => {
      expect(api.getSourceConfig).toHaveBeenCalledWith('qc-bag-result');
    });

    // Should show drawer with detail panel title
    await waitFor(() => {
      expect(screen.getByText('Source Configuration Details')).toBeInTheDocument();
    });
  });

  it('closes drawer when close button is clicked', async () => {
    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('row-qc-bag-result')).toBeInTheDocument();
    });

    // Open drawer
    fireEvent.click(screen.getByTestId('row-qc-bag-result'));

    await waitFor(() => {
      expect(screen.getByText('Source Configuration Details')).toBeInTheDocument();
    });

    // Click close button
    fireEvent.click(screen.getByRole('button', { name: /close/i }));

    // Drawer should close (title should not be visible)
    await waitFor(() => {
      expect(screen.queryByText('Source Configuration Details')).not.toBeInTheDocument();
    });
  });

  it('shows error in drawer when detail fetch fails', async () => {
    vi.mocked(api.getSourceConfig).mockRejectedValue(new Error('Not found'));

    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByTestId('row-qc-bag-result')).toBeInTheDocument();
    });

    // Click on a row
    fireEvent.click(screen.getByTestId('row-qc-bag-result'));

    // Should show error in drawer
    await waitFor(() => {
      expect(screen.getByText('Not found')).toBeInTheDocument();
    });
  });

  it('filters data client-side by search query', async () => {
    renderWithRouter(<SourceConfigList />);

    await waitFor(() => {
      expect(screen.getByText('QC Bag Results')).toBeInTheDocument();
    });

    // Type in search box
    fireEvent.change(screen.getByTestId('search-input'), { target: { value: 'weather' } });

    // Should filter to only show weather data
    await waitFor(() => {
      expect(screen.getByText('Weather Data')).toBeInTheDocument();
      expect(screen.queryByText('QC Bag Results')).not.toBeInTheDocument();
    });
  });
});
