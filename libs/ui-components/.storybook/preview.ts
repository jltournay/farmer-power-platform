import type { Preview } from '@storybook/react';
import { ThemeProvider } from '../src/theme';
import React from 'react';

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'warm-white',
      values: [
        { name: 'warm-white', value: '#FFFDF9' },
        { name: 'white', value: '#FFFFFF' },
        { name: 'dark', value: '#1B4332' },
      ],
    },
  },
  decorators: [
    (Story) => {
      return React.createElement(ThemeProvider, null, React.createElement(Story));
    },
  ],
};

export default preview;
