/**
 * Pantheon 2.0 Mobile App
 * Entry point — registers root component with React Native runtime.
 */
import { AppRegistry } from 'react-native';
import App from './src/App';
import { name as appName } from './app.json';

AppRegistry.registerComponent(appName, () => App);
