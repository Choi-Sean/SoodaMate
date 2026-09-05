import { Platform } from 'react-native';
import { registerRootComponent } from 'expo';

import App from './App';

// Firebase requires the background message handler registered outside the
// React tree, at module scope. Guarded because @react-native-firebase has no
// web build and (until a real Firebase project exists) may not even be
// linked natively — same no-op-until-configured pattern used everywhere else
// Firebase/Kakao/AdMob show up in this app.
if (Platform.OS !== 'web') {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const messaging = require('@react-native-firebase/messaging').default;
    messaging().setBackgroundMessageHandler(async () => {
      // FCM already displays the system notification for data+notification
      // payloads; nothing extra to do here for v1.
    });
  } catch {
    // native module not present yet — fine, registerForPushNotifications()
    // in src/services/pushNotifications.ts no-ops the same way at login.
  }
}

// registerRootComponent calls AppRegistry.registerComponent('main', () => App);
// It also ensures that whether you load the app in Expo Go or in a native build,
// the environment is set up appropriately
registerRootComponent(App);
