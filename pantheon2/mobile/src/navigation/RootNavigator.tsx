/**
 * RootNavigator.tsx — React Navigation stack for Pantheon 2.0.
 *
 * Stack:
 *   PreSession  → LiveHUD (on GO)
 *   LiveHUD     → MutationReview (on session end)
 *   MutationReview → MirrorReport (on all mutations resolved)
 *   MirrorReport → PreSession (on done)
 *
 * Dark theme throughout. Landscape lock enforced on LiveHUDScreen.
 */

import React from 'react';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../types';

import PreSessionScreen from '../screens/PreSessionScreen';
import LiveHUDScreen from '../screens/LiveHUDScreen';
import MutationReviewScreen from '../screens/MutationReviewScreen';
import MirrorReportScreen from '../screens/MirrorReportScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

const PantheonDarkTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: '#030712',
    card: '#111827',
    border: '#1f2937',
    text: '#f3f4f6',
    primary: '#6366f1',
    notification: '#ef4444',
  },
};

const RootNavigator: React.FC = () => {
  return (
    <NavigationContainer theme={PantheonDarkTheme}>
      <Stack.Navigator
        initialRouteName="PreSession"
        screenOptions={{
          headerStyle: { backgroundColor: '#111827' },
          headerTintColor: '#f3f4f6',
          headerTitleStyle: { fontWeight: '700', fontSize: 14, letterSpacing: 0.5 },
          contentStyle: { backgroundColor: '#030712' },
          animation: 'slide_from_right',
        }}
      >
        <Stack.Screen
          name="PreSession"
          component={PreSessionScreen}
          options={{ title: 'PANTHEON — SESSION PREP', headerShown: true }}
        />
        <Stack.Screen
          name="LiveHUD"
          component={LiveHUDScreen}
          options={{
            title: '',
            headerShown: false,
            orientation: 'landscape',
            animation: 'fade',
          }}
        />
        <Stack.Screen
          name="MutationReview"
          component={MutationReviewScreen}
          options={{ title: 'GENOME REVIEW', headerShown: true }}
        />
        <Stack.Screen
          name="MirrorReport"
          component={MirrorReportScreen}
          options={{ title: 'MIRROR REPORT', headerShown: true }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default RootNavigator;
