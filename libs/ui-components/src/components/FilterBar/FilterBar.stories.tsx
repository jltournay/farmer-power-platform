import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { fn } from '@storybook/test';
import { FilterBar, FilterValues } from './FilterBar';

const statusOptions = [
  { value: 'win', label: 'WIN' },
  { value: 'watch', label: 'WATCH' },
  { value: 'action', label: 'ACTION' },
];

const regionOptions = [
  { value: 'nyeri', label: 'Nyeri' },
  { value: 'kiambu', label: 'Kiambu' },
  { value: 'meru', label: 'Meru' },
  { value: 'kisumu', label: 'Kisumu' },
];

const factoryOptions = [
  { value: 'nyeri-001', label: 'Nyeri Tea Factory' },
  { value: 'kiambu-001', label: 'Kiambu Tea Factory' },
  { value: 'meru-001', label: 'Meru Tea Factory' },
];

const meta: Meta<typeof FilterBar> = {
  component: FilterBar,
  title: 'DataDisplay/FilterBar',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof FilterBar>;

/** Basic filter bar with search and one filter */
export const Basic: Story = {
  args: {
    filters: [
      { id: 'status', label: 'Status', options: statusOptions },
    ],
    searchTerm: '',
    searchPlaceholder: 'Search farmers...',
    onSearchChange: fn(),
    onFilterChange: fn(),
  },
};

/** Multiple filters */
export const MultipleFilters: Story = {
  args: {
    filters: [
      { id: 'status', label: 'Status', options: statusOptions },
      { id: 'region', label: 'Region', options: regionOptions },
      { id: 'factory', label: 'Factory', options: factoryOptions },
    ],
    searchTerm: '',
    searchPlaceholder: 'Search farmers...',
    onSearchChange: fn(),
    onFilterChange: fn(),
  },
};

/** With active filters and clear all */
export const WithActiveFilters: Story = {
  args: {
    filters: [
      { id: 'status', label: 'Status', options: statusOptions },
      { id: 'region', label: 'Region', options: regionOptions },
    ],
    filterValues: { status: 'action', region: 'nyeri' },
    searchTerm: 'kamau',
    searchPlaceholder: 'Search farmers...',
    onSearchChange: fn(),
    onFilterChange: fn(),
    onClearAll: fn(),
  },
};

/** Interactive filter bar */
export const Interactive: Story = {
  render: function InteractiveFilterBar() {
    const [filters, setFilters] = useState<FilterValues>({
      status: '',
      region: '',
    });
    const [search, setSearch] = useState('');

    const handleFilterChange = (filterId: string, value: string | string[]) => {
      setFilters((prev) => ({ ...prev, [filterId]: value }));
    };

    const handleClearAll = () => {
      setFilters({ status: '', region: '' });
      setSearch('');
    };

    return (
      <FilterBar
        filters={[
          { id: 'status', label: 'Status', options: statusOptions },
          { id: 'region', label: 'Region', options: regionOptions },
        ]}
        filterValues={filters}
        onFilterChange={handleFilterChange}
        searchTerm={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search farmers..."
        onClearAll={handleClearAll}
      />
    );
  },
};

/** Search only (no filters) */
export const SearchOnly: Story = {
  args: {
    filters: [],
    searchTerm: '',
    searchPlaceholder: 'Search...',
    onSearchChange: fn(),
  },
};

/** Filters only (no search) */
export const FiltersOnly: Story = {
  args: {
    filters: [
      { id: 'status', label: 'Status', options: statusOptions },
      { id: 'region', label: 'Region', options: regionOptions },
    ],
    showSearch: false,
    onFilterChange: fn(),
  },
};

/** Multi-select filter */
export const MultiSelect: Story = {
  args: {
    filters: [
      { id: 'status', label: 'Status', options: statusOptions, multiple: true },
      { id: 'region', label: 'Region', options: regionOptions },
    ],
    filterValues: { status: ['win', 'watch'], region: '' },
    searchTerm: '',
    onSearchChange: fn(),
    onFilterChange: fn(),
    onClearAll: fn(),
  },
};
