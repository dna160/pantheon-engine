/**
 * PreSessionScreen.tsx — Pre-session setup and GO gate.
 *
 * Displays:
 *   1. Genome confidence badge (ALWAYS — Constraint #4)
 *   2. RWI score + window status
 *   3. Psych review flags (HIGH must be acknowledged — Constraint #5)
 *   4. GO button (disabled until all HIGH flags acknowledged)
 *
 * Data flow:
 *   - Calls SessionService.prepareSession() on mount
 *   - Calls SessionService.acknowledgeFlag() per HIGH flag
 *   - Calls SessionService.startSession() on GO → navigates to LiveHUD
 *
 * Per PRD CLAUDE.md Critical Constraint #5:
 *   HIGH flags must be acknowledged. Session cannot start until all are confirmed.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList, PreSessionPayload, PsychFlag } from '../types';
import SessionService from '../services/SessionService';
import { useHUDStore } from '../services/HUDStateManager';
import ConfidenceBadge from '../components/ConfidenceBadge';
import RWIIndicator from '../components/RWIIndicator';
import PsychWarningCard from '../components/PsychWarningCard';

type Props = NativeStackScreenProps<RootStackParamList, 'PreSession'>;

const PreSessionScreen: React.FC<Props> = ({ navigation, route }) => {
  const prospectId = route.params?.prospectId ?? 'demo';

  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [payload, setPayload] = useState<PreSessionPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [acknowledgedIds, setAcknowledgedIds] = useState<Set<string>>(new Set());

  const setSessionActive = useHUDStore(s => s.setSessionActive);

  // Load pre-session data on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await SessionService.prepareSession(prospectId);
        if (!cancelled) {
          setPayload(data);
          setLoading(false);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'Failed to load session data';
          setError(msg);
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [prospectId]);

  const highFlags: PsychFlag[] = (payload?.psych_flags ?? []).filter(f => f.severity === 'HIGH');
  const moderateFlags: PsychFlag[] = (payload?.psych_flags ?? []).filter(f => f.severity === 'MODERATE');

  const allHighAcknowledged = highFlags.every(f => acknowledgedIds.has(f.flag_id));
  const canGo = !!payload && allHighAcknowledged && !starting;

  const handleAcknowledge = useCallback(async (flagId: string) => {
    try {
      await SessionService.acknowledgeFlag(flagId);
      setAcknowledgedIds(prev => new Set([...prev, flagId]));
    } catch {
      // Acknowledge optimistically — flag on server is best-effort
      setAcknowledgedIds(prev => new Set([...prev, flagId]));
    }
  }, []);

  const handleGo = useCallback(async () => {
    if (!canGo || !payload) return;
    setStarting(true);
    try {
      const { session_id } = await SessionService.startSession(prospectId);
      setSessionActive(true, session_id);
      navigation.replace('LiveHUD', { sessionId: session_id });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to start session';
      Alert.alert('Start Failed', msg);
      setStarting(false);
    }
  }, [canGo, payload, prospectId, navigation, setSessionActive]);



  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.loadingText}>Loading session data…</Text>
      </View>
    );
  }

  if (error || !payload) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>⚠ {error ?? 'Unknown error'}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={() => setLoading(true)}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Prospect header */}
      <View style={styles.prospectHeader}>
        <Text style={styles.prospectLabel}>PROSPECT</Text>
        <Text style={styles.prospectName}>{payload.prospect_name}</Text>
        <Text style={styles.prospectRole}>{payload.role} · {payload.company}</Text>
      </View>

      {/* Genome confidence — ALWAYS shown (Constraint #4) */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>GENOME CONFIDENCE</Text>
        <ConfidenceBadge badge={payload.confidence_badge} />
      </View>

      {/* RWI */}
      <View style={styles.section}>
        <RWIIndicator score={payload.rwi.score} status={payload.rwi.window_status} />
      </View>

      {/* Psych review — HIGH flags */}
      {highFlags.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>⛔ PSYCH FLAGS — ACKNOWLEDGMENT REQUIRED</Text>
          <View style={styles.flagList}>
            {highFlags.map(flag => (
              <PsychWarningCard
                key={flag.flag_id}
                flag={flag}
                acknowledged={acknowledgedIds.has(flag.flag_id)}
                onAcknowledge={handleAcknowledge}
              />
            ))}
          </View>
        </View>
      )}

      {/* Psych review — MODERATE flags */}
      {moderateFlags.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>⚠ ADVISORY FLAGS</Text>
          <View style={styles.flagList}>
            {moderateFlags.map(flag => (
              <PsychWarningCard
                key={flag.flag_id}
                flag={flag}
                acknowledged={acknowledgedIds.has(flag.flag_id)}
                onAcknowledge={handleAcknowledge}
              />
            ))}
          </View>
        </View>
      )}

      {/* GO gate hint */}
      {highFlags.length > 0 && !allHighAcknowledged && (
        <View style={styles.gateHint}>
          <Text style={styles.gateHintText}>
            Acknowledge all ⛔ flags above to unlock GO
          </Text>
        </View>
      )}

      {/* GO button */}
      <TouchableOpacity
        style={[styles.goButton, !canGo && styles.goButtonDisabled]}
        onPress={handleGo}
        disabled={!canGo}
        activeOpacity={0.85}
      >
        {starting ? (
          <ActivityIndicator color="#030712" />
        ) : (
          <Text style={[styles.goText, !canGo && styles.goTextDisabled]}>GO</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#030712',
  },
  content: {
    padding: 16,
    gap: 16,
    paddingBottom: 40,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
    backgroundColor: '#030712',
  },
  loadingText: {
    color: '#6b7280',
    fontSize: 13,
  },
  errorText: {
    color: '#f87171',
    fontSize: 14,
    textAlign: 'center',
    paddingHorizontal: 24,
  },
  retryButton: {
    backgroundColor: '#1f2937',
    borderRadius: 8,
    paddingHorizontal: 20,
    paddingVertical: 10,
    marginTop: 8,
  },
  retryText: {
    color: '#f3f4f6',
    fontWeight: '600',
  },
  prospectHeader: {
    gap: 2,
  },
  prospectLabel: {
    fontSize: 9,
    color: '#6b7280',
    fontWeight: '600',
    letterSpacing: 1,
  },
  prospectName: {
    fontSize: 20,
    color: '#f9fafb',
    fontWeight: '700',
  },
  prospectRole: {
    fontSize: 13,
    color: '#9ca3af',
  },
  section: {
    gap: 6,
  },
  sectionLabel: {
    fontSize: 9,
    color: '#6b7280',
    fontWeight: '600',
    letterSpacing: 0.8,
  },
  flagList: {
    gap: 8,
  },
  gateHint: {
    backgroundColor: '#1c1917',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  gateHintText: {
    color: '#9ca3af',
    fontSize: 12,
    fontStyle: 'italic',
  },
  goButton: {
    backgroundColor: '#4ade80',
    borderRadius: 12,
    paddingVertical: 18,
    alignItems: 'center',
    marginTop: 8,
  },
  goButtonDisabled: {
    backgroundColor: '#1f2937',
  },
  goText: {
    color: '#030712',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 3,
  },
  goTextDisabled: {
    color: '#4b5563',
  },
});

export default PreSessionScreen;
