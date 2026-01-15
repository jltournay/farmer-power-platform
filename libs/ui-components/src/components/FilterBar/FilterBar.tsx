/**
 * FilterBar Component
 *
 * Combined dropdown filters + search input for filtering data.
 * Provides consistent filtering UI across admin interfaces.
 *
 * Accessibility:
 * - All inputs have labels (visible or aria-label)
 * - Focus ring: 3px Forest Green outline
 * - Clear button accessible via keyboard
 */

import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  InputAdornment,
  useTheme,
  Chip,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import type { SelectChangeEvent } from '@mui/material';

/** Filter option for dropdowns */
export interface FilterOption {
  /** Unique value */
  value: string;
  /** Display label */
  label: string;
}

/** Filter definition */
export interface FilterDef {
  /** Unique filter ID */
  id: string;
  /** Filter label */
  label: string;
  /** Available options */
  options: FilterOption[];
  /** Whether multiple selection is allowed */
  multiple?: boolean;
}

/** Current filter values */
export type FilterValues = Record<string, string | string[]>;

/** FilterBar component props */
export interface FilterBarProps {
  /** Filter definitions */
  filters?: FilterDef[];
  /** Current filter values */
  filterValues?: FilterValues;
  /** Filter change handler */
  onFilterChange?: (filterId: string, value: string | string[]) => void;
  /** Search term */
  searchTerm?: string;
  /** Search change handler */
  onSearchChange?: (term: string) => void;
  /** Search placeholder text */
  searchPlaceholder?: string;
  /** Whether to show search input */
  showSearch?: boolean;
  /** Clear all filters handler */
  onClearAll?: () => void;
  /** Whether any filters are active */
  hasActiveFilters?: boolean;
}

/**
 * FilterBar provides filtering controls for data lists.
 *
 * @example
 * ```tsx
 * <FilterBar
 *   filters={[
 *     { id: 'status', label: 'Status', options: [
 *       { value: 'win', label: 'WIN' },
 *       { value: 'watch', label: 'WATCH' },
 *       { value: 'action', label: 'ACTION' },
 *     ]},
 *     { id: 'region', label: 'Region', options: regions },
 *   ]}
 *   filterValues={{ status: 'win', region: '' }}
 *   onFilterChange={(id, value) => setFilters(prev => ({ ...prev, [id]: value }))}
 *   searchTerm={search}
 *   onSearchChange={setSearch}
 *   searchPlaceholder="Search farmers..."
 * />
 * ```
 */
export function FilterBar({
  filters = [],
  filterValues = {},
  onFilterChange,
  searchTerm = '',
  onSearchChange,
  searchPlaceholder = 'Search...',
  showSearch = true,
  onClearAll,
  hasActiveFilters,
}: FilterBarProps): JSX.Element {
  const theme = useTheme();

  const handleFilterChange = (filterId: string) => (event: SelectChangeEvent<string | string[]>) => {
    onFilterChange?.(filterId, event.target.value);
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onSearchChange?.(event.target.value);
  };

  const handleClearSearch = () => {
    onSearchChange?.('');
  };

  // Calculate if there are active filters
  const activeFiltersCount =
    Object.values(filterValues).filter((v) => (Array.isArray(v) ? v.length > 0 : v !== '')).length +
    (searchTerm ? 1 : 0);
  const showClearAll = hasActiveFilters ?? activeFiltersCount > 0;

  return (
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 2,
        alignItems: 'center',
        mb: 2,
        p: 2,
        backgroundColor: 'background.paper',
        borderRadius: 1,
        border: `1px solid ${theme.palette.divider}`,
      }}
    >
      {/* Search input */}
      {showSearch && (
        <TextField
          size="small"
          placeholder={searchPlaceholder}
          value={searchTerm}
          onChange={handleSearchChange}
          aria-label="Search"
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              ),
              endAdornment: searchTerm ? (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    onClick={handleClearSearch}
                    aria-label="Clear search"
                    sx={{
                      '&:focus': {
                        outline: `3px solid ${theme.palette.primary.main}`,
                        outlineOffset: '2px',
                      },
                    }}
                  >
                    <ClearIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ) : null,
            },
          }}
          sx={{
            minWidth: 200,
            flex: { xs: '1 1 100%', sm: '0 1 auto' },
            '& .MuiOutlinedInput-root:focus-within': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        />
      )}

      {/* Filter dropdowns */}
      {filters.map((filter) => (
        <FormControl
          key={filter.id}
          size="small"
          sx={{
            minWidth: 140,
            '& .MuiOutlinedInput-root:focus-within': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            },
          }}
        >
          <InputLabel id={`filter-${filter.id}-label`}>{filter.label}</InputLabel>
          <Select
            labelId={`filter-${filter.id}-label`}
            id={`filter-${filter.id}`}
            value={filterValues[filter.id] ?? (filter.multiple ? [] : '')}
            onChange={handleFilterChange(filter.id)}
            label={filter.label}
            multiple={filter.multiple}
            renderValue={(selected) => {
              if (filter.multiple && Array.isArray(selected)) {
                return selected.length > 0 ? (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip
                        key={value}
                        label={filter.options.find((o) => o.value === value)?.label ?? value}
                        size="small"
                      />
                    ))}
                  </Box>
                ) : null;
              }
              return filter.options.find((o) => o.value === selected)?.label ?? selected;
            }}
          >
            {!filter.multiple && (
              <MenuItem value="">
                <em>All</em>
              </MenuItem>
            )}
            {filter.options.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      ))}

      {/* Clear all button */}
      {showClearAll && onClearAll && (
        <Box sx={{ flex: { xs: '1 1 100%', sm: '0 1 auto' } }}>
          <Chip
            label={`Clear all (${activeFiltersCount})`}
            onDelete={onClearAll}
            onClick={onClearAll}
            variant="outlined"
            sx={{
              cursor: 'pointer',
              '&:focus': {
                outline: `3px solid ${theme.palette.primary.main}`,
                outlineOffset: '2px',
              },
            }}
          />
        </Box>
      )}
    </Box>
  );
}

export default FilterBar;
