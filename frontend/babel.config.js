module.exports = {
  presets: ['module:@react-native/babel-preset'],
  plugins: [
    [
      'module-resolver',
      {
        // No `root: ['./src']`. It makes src a bare-specifier resolution root,
        // so `import { createStore } from 'redux'` inside redux-persist
        // resolves to src/redux instead of the npm package. Explicit aliases
        // only — they cannot collide with package names.
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
        alias: {
          '@api': './src/api',
          '@components': './src/components',
          '@constants': './src/constants',
          '@navigation': './src/AppNavigation',
          '@redux': './src/redux',
          '@screens': './src/screens',
          '@assets': './src/assets',
          // Deliberately NOT '@types': module-resolver matches aliases by
          // prefix, so '@types' would also capture '@types/react' and every
          // other DefinitelyTyped package and try to resolve them inside src.
          '@models': './src/types',
        },
      },
    ],
  ],
};
