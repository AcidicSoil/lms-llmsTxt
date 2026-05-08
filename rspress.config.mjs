import { defineConfig } from '@rspress/core';

export default defineConfig({
  root: 'docs',
  title: 'LM Studio llms.txt Generator',
  description:
    'Generate llms.txt, llms-full, optional llms-ctx, fallback JSON, and graph artifacts for GitHub repositories.',
  logoText: 'lms-llmsTxt',
  route: {
    cleanUrls: true,
  },
  search: {
    codeBlocks: true,
  },
});
