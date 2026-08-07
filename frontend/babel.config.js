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

// Reads .env at build time and inlines the values, so there is no native
// module and no Gradle change — the alternative, react-native-config, needs
// both and would have to be re-linked on every clean build.
//
// Inlined means baked into the bundle: these are addresses and feature flags,
// never secrets. An API key here would ship inside the APK, where anyone can
// read it. Secrets stay on the backend.
const dotenv = [
  'module:react-native-dotenv',
  {
    moduleName: '@env',
    path: '.env',
    // Missing .env is not an error: a fresh clone should build, and
    // src/api/config.ts supplies defaults for everything.
    allowUndefined: true,
  },
];

module.exports = {
  presets: ['module:@react-native/babel-preset'],
  plugins: [resolver(ALIASES), dotenv],
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
        // Repeated, not inherited: an `env` block replaces the plugin list
        // rather than merging with it, which is exactly how the aliases were
        // lost from release builds once already.
        dotenv,
      ],
    },
  },
};
