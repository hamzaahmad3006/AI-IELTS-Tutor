/**
 * @format
 */

import 'react-native-gesture-handler';
import { registerGlobals } from '@livekit/react-native';
import { AppRegistry } from 'react-native';
import App from './App';
import { name as appName } from './app.json';

// Installs the WebRTC globals (RTCPeerConnection, MediaStream,
// navigator.mediaDevices) that livekit-client expects to find. It is a browser
// SDK underneath, and without this it fails at connect time complaining about
// an undefined constructor rather than about setup.
//
// Here rather than in App.tsx: it has to run before any module that touches
// those globals is imported, and App pulls in the whole navigation tree.
registerGlobals();

AppRegistry.registerComponent(appName, () => App);
