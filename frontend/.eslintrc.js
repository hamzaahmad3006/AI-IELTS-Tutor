module.exports = {
  root: true,
  extends: '@react-native',
  rules: {
    // Every "inline style" in this codebase is a theme lookup —
    // `backgroundColor: theme.colors.card` and the like. Those cannot live in
    // StyleSheet.create, which is evaluated once at module load with no access
    // to the active theme. Static styling still goes in StyleSheet.
    'react-native/no-inline-styles': 'off',

    // `void somePromise` is the deliberate marker for "not awaited on purpose",
    // used for fire-and-forget calls whose failure is handled inside. Dropping
    // it would make genuinely floating promises indistinguishable from
    // intentional ones.
    'no-void': 'off',

    // `tabBarIcon` and friends are render props, not nested component
    // definitions; React Navigation's API is built around them.
    'react/no-unstable-nested-components': ['warn', { allowAsProps: true }],
  },
  overrides: [
    {
      // Detox specs run in their own environment: `device`, `element`, `by`
      // and `waitFor` are injected globals. Scoped here rather than declared
      // project-wide, so a stray `device` in app code is still an error.
      files: ['e2e/**/*.e2e.js'],
      env: { jest: true, node: true },
      globals: {
        device: 'readonly',
        element: 'readonly',
        by: 'readonly',
        waitFor: 'readonly',
      },
    },
    {
      files: ['**/__tests__/**/*.{ts,tsx}'],
      rules: {
        // Test harnesses legitimately define a component inline to drive a
        // stateful flow through a controlled component.
        'react/no-unstable-nested-components': 'off',
      },
    },
  ],
};
