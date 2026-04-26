/**
 * App.tsx — Pantheon 2.0 React Native root component.
 *
 * Mounts RootNavigator. No logic here — all state lives in
 * Zustand stores and screen-level components.
 */

import React from 'react';
import { StatusBar } from 'react-native';
import RootNavigator from './navigation/RootNavigator';

const App: React.FC = () => {
  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor="#111827" />
      <RootNavigator />
    </>
  );
};

export default App;
