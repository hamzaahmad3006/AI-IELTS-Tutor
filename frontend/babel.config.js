// Path aliases, shared between the default and production configurations.
//
// They are built from one object rather than written twice because Babel
// identifies plugins by name: a second `module-resolver` under `env.production`
// does not merge with this one, it *replaces* it. Listing only the alias that
// differs there silently dropped every other alias from release builds, and the
// bundle failed on `Unable to resolve module @api`.
const ALIASES = {
  '@api': './src/api',
  '@components': './src/components',
  '@constants': './src/constants',
  '@navigation': './src/AppNavigation',
  '@redux': './src/redux',
  '@screens': './src/screens',
  '@assets': './src/assets',
  // Deliberately NOT '@types': module-resolver matches aliases by prefix, so
  // '@types' would also capture '@types/react' and every other DefinitelyTyped
  // package and try to resolve them inside src.
  '@models': './src/types',
  // Development fixtures. Aliased rather than imported relatively so a release
  // build can point the same specifier at a stub — see `env.production`.
  '@fixtures': './src/api/mock/fixtures',
};

const resolver = aliases => [
  'module-resolver',
  {
    // No `root: ['./src']`. It makes src a bare-specifier resolution root, so
    // `import { createStore } from 'redux'` inside redux-persist resolves to
    // src/redux instead of the npm package. Explicit aliases only — they
    // cannot collide with package names.
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    alias: aliases,
  },
];

module.exports = {
  presets: ['module:@react-native/babel-preset'],
  plugins: [resolver(ALIASES)],
  env: {
    production: {
      plugins: [
        // The full map with one entry swapped. The fixtures are unreachable in
        // release anyway (`__DEV__` is false), but unreachable is not the same
        // as unbundled: Metro builds its graph from imports, not from what
        // runs, so ~14 KB of invented essays and bands shipped regardless.
        resolver({
          ...ALIASES,
          '@fixtures': './src/api/mock/fixtures.stub',
        }),
      ],
    },
  },
};
