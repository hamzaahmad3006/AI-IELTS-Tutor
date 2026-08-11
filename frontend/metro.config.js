const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

/**
 * Metro configuration
 * https://reactnative.dev/docs/metro
 *
 * The blockList is the only addition, and it is not cosmetic: Metro's file
 * watcher crashes outright when a directory it is watching disappears
 * underneath it, and the native build writes and deletes thousands of CMake
 * scratch directories under `node_modules/<pkg>/android/.cxx/`.
 *
 * The symptom is misleading. Metro dies with an ENOENT on a path nobody
 * imports, and the next thing anyone sees is the app on the device showing
 * "Unable to load script" — which reads as a bundler that was never started,
 * or as a missing `adb reverse`, and sends you looking in the wrong place.
 *
 * Nothing here is ever imported, so excluding it costs nothing.
 *
 * @type {import('@react-native/metro-config').MetroConfig}
 */
// A plain RegExp rather than metro-config's `exclusionList` helper, whose
// subpath this version of the package no longer exports. `blockList` takes a
// RegExp directly, so the helper only ever saved an alternation.
//
// Both separators are matched because the paths are Windows-native here and
// POSIX in CI.
const config = {
  resolver: {
    blockList:
      // Native build scratch: CMake, Gradle, and the per-ABI object trees,
      // plus the release-bundle check's output directory.
      /[\\/]android[\\/](\.cxx|build)[\\/]|[\\/]android[\\/]app[\\/]build[\\/]|[\\/]\.bundle-check[\\/]/,
  },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
