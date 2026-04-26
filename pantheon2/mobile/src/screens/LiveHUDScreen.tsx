/**
 * LiveHUDScreen.tsx — Live session phone HUD (landscape).
 *
 * Reads HUD state exclusively from HUDStateManager (Zustand + WebSocket).
 * Zone 2 — no backend API calls during live session.
 *
 * Layout (landscape, two columns):
 *   LEFT COLUMN:
 *     - MomentTypeLabel (current classified moment)
 *     - ConfidenceBadge (genome confidence — Constraint #4)
 *     - RWIIndicator (compact)
 *     - HookCloseBar (hook)
 *     - HookCloseBar (close)
 *     - DivergenceAlert (when active)
 *
 *   RIGHT COLUMN:
 *     - DialogOptions (3 options sorted by probability)
 *     - HiddenSignalPanel (Stream B paralinguistics)
 *
 * END SESSION button → calls endSession() → navigates to MutationReview.
 */

import React, { useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../types';
import { useHUDStore, HUDWebSocketManager } from '../services/HUDStateManager';
import SessionService from '../services/SessionService';
import MomentTypeLabel from '../components/MomentTypeLabel';
import ConfidenceBadge from '../components/ConfidenceBadge';
import RWIIndicator from '../components/RWIIndicator';
import HookCloseBar from '../components/HookCloseBar';
import DialogOptions from '../components/DialogOptions';
import HiddenSignalPanel from '../components/HiddenSignalPanel';
import DivergenceAlert from '../components/DivergenceAlert';

type Props = NativeStackScreenProps<RootStackParamList, 'LiveHUD'>;

const LiveHUDScreen: React.FC<Props> = ({ navigation, route }) => {
  const { sessionId } = route.params;
  const wsRef = useRef<HUDWebSocketManager | null>(null);

  const hud = useHUDStore(s => s.hud);
  const wsConnected = useHUDStore(s => s.wsConnected);
  const setSessionActive = useHUDStore(s => s.setSessionActive);
  const resetSession = useHUDStore(s => s.resetSession);

  const selectedKey = useHUDStore(s => s.hud?.selected_key ?? null);

  // Connect WebSocket on mount
  useEffect(() => {
    const ws = new HUDWebSocketManager(sessionId);
    wsRef.current = ws;
    ws.connect();
    return () => {
      ws.disconnect();
    };
  }, [sessionId, updateHUD, updateBarsOnly, setWSConnected]);

  const handleSelectOption = useCallback(
    async (key: 'option_a' | 'option_b' | 'option_c') => {
      try {
        await SessionService.recordOptionChoice(sessionId, key);
      } catch {
        // Non-blocking — best effort logging
      }
    },
    [sessionId],
  );

  const handleEndSession = useCallback(() => {
    Alert.alert(
      'End Session',
      'Are you sure? This will stop recording and begin post-session analysis.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'End Session',
          style: 'destructive',
          onPress: async () => {
            try {
              wsRef.current?.disconnect();
              await SessionService.endSession(sessionId);
              setSessionActive(false);
              navigation.replace('MutationReview', { sessionId });
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : 'Failed to end session';
              Alert.alert('Error', msg);
            }
          },
        },
      ],
    );
  }, [sessionId, navigation, setSessionActive]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      resetSession();
    };
  }, [resetSession]);

  if (!hud) {
    return (
      <View style={styles.waiting}>
        <Text style={styles.waitingText}>
          {wsConnected ? 'Waiting for session data…' : 'Connecting…'}
        </Text>
        <View style={[styles.wsIndicator, wsConnected ? styles.wsOn : styles.wsOff]} />
      </View>
    );
  }

  const showDivergence = hud.divergence_alert?.active ?? false;

  return (
    <View style={styles.root}>
      {/* LEFT column */}
      <View style={styles.leftColumn}>
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.leftContent}>
          {/* Moment + confidence row */}
          <View style={styles.topRow}>
            <MomentTypeLabel
              momentType={hud.moment_type}
              confidence={hud.classification_confidence}
            />
            <ConfidenceBadge badge={hud.confidence_badge} size="small" />
          </View>

          {/* RWI */}
          <RWIIndicator
            score={hud.rwi_live.score}
            status={hud.rwi_live.window_status}
            compact
          />

          {/* Bars */}
          <HookCloseBar barState={hud.bars} />

          {/* Divergence alert */}
          {showDivergence && hud.divergence_alert && (
            <DivergenceAlert alert={hud.divergence_alert} />
          )}

          {/* Elapsed + WS status */}
          <View style={styles.footer}>
            <Text style={styles.elapsed}>{formatElapsed(hud.elapsed_seconds ?? 0)}</Text>
            <View style={[styles.wsIndicator, wsConnected ? styles.wsOn : styles.wsOff]} />
          </View>
        </ScrollView>

        {/* End session button — bottom of left col */}
        <TouchableOpacity style={styles.endButton} onPress={handleEndSession}>
          <Text style={styles.endButtonText}>END</Text>
        </TouchableOpacity>
      </View>

      {/* RIGHT column */}
      <View style={styles.rightColumn}>
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.rightContent}>
          {hud.selection && (
            <DialogOptions
              options={hud.selection}
              onSelect={handleSelectOption}
              selectedKey={selectedKey}
            />
          )}

          {hud.para && (
            <HiddenSignalPanel para={hud.para} />
          )}
        </ScrollView>
      </View>
    </View>
  );
};

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: '#030712',
  },
  leftColumn: {
    width: '38%',
    borderRightWidth: 1,
    borderRightColor: '#1f2937',
    flexDirection: 'column',
  },
  leftContent: {
    padding: 12,
    gap: 10,
  },
  rightColumn: {
    flex: 1,
  },
  rightContent: {
    padding: 12,
    gap: 10,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  elapsed: {
    fontSize: 11,
    color: '#6b7280',
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
  },
  wsIndicator: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  wsOn: {
    backgroundColor: '#22c55e',
  },
  wsOff: {
    backgroundColor: '#ef4444',
  },
  endButton: {
    backgroundColor: '#1f2937',
    margin: 12,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#374151',
  },
  endButtonText: {
    color: '#f87171',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  waiting: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#030712',
    gap: 12,
  },
  waitingText: {
    color: '#6b7280',
    fontSize: 13,
  },
});

export default LiveHUDScreen;
