/**
 * MirrorReportScreen.tsx — Post-session practitioner mirror report.
 *
 * Displays 4 observations from MirrorReportPayload.
 * NEVER shown on live HUD — post-session only (Constraint #6).
 *
 * Per PRD CLAUDE.md Critical Constraint #6:
 *   "Nothing from mirror_report.py appears on the live HUD."
 *   This screen is reachable only via navigation from MutationReviewScreen.
 *   It has no WebSocket connection and makes no Zone 2 calls.
 *
 * Layout:
 *   - Session summary (duration, moment distribution, option choices)
 *   - 4 observation cards (what worked, what didn't, pattern, next-session focus)
 *   - Done button → returns to PreSession
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList, MirrorReportPayload } from '../types';
import SessionService from '../services/SessionService';

type Props = NativeStackScreenProps<RootStackParamList, 'MirrorReport'>;

interface ObservationCardProps {
  index: number;
  label: string;
  text: string;
  color: string;
}

const OBSERVATION_META: { label: string; color: string; icon: string }[] = [
  { label: 'WHAT WORKED',         color: '#22c55e', icon: '✓' },
  { label: 'WHAT DIDN\'T',        color: '#ef4444', icon: '✗' },
  { label: 'PATTERN DETECTED',    color: '#6366f1', icon: '⟳' },
  { label: 'NEXT SESSION FOCUS',  color: '#f59e0b', icon: '→' },
];

const ObservationCard: React.FC<ObservationCardProps> = ({ index, label, text, color }) => {
  const meta = OBSERVATION_META[index] ?? { label, color, icon: '•' };
  return (
    <View style={[styles.obsCard, { borderLeftColor: meta.color }]}>
      <View style={styles.obsHeader}>
        <Text style={[styles.obsIcon, { color: meta.color }]}>{meta.icon}</Text>
        <Text style={[styles.obsLabel, { color: meta.color }]}>{meta.label}</Text>
      </View>
      <Text style={styles.obsText}>{text}</Text>
    </View>
  );
};

const MirrorReportScreen: React.FC<Props> = ({ navigation, route }) => {
  const { sessionId } = route.params;

  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<MirrorReportPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await SessionService.getMirrorReport(sessionId);
        if (!cancelled) {
          setReport(data);
          setLoading(false);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'Report unavailable';
          setError(msg);
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleDone = () => {
    navigation.popToTop();
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.subText}>Generating mirror report…</Text>
      </View>
    );
  }

  if (error || !report) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>⚠ {error ?? 'Report unavailable'}</Text>
        <TouchableOpacity style={styles.doneButton} onPress={handleDone}>
          <Text style={styles.doneText}>Done</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const observations = [
    report.what_worked,
    report.what_didnt,
    report.pattern_detected,
    report.next_session_focus,
  ];

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.postSessionTag}>POST-SESSION ONLY</Text>
        <Text style={styles.title}>Mirror Report</Text>
        <Text style={styles.subtitle}>Session {sessionId.slice(-8)}</Text>
      </View>

      {/* Session summary strip */}
      <View style={styles.summaryStrip}>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryLabel}>DURATION</Text>
          <Text style={styles.summaryValue}>{report.session_duration_min}m</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <Text style={styles.summaryLabel}>MOMENTS</Text>
          <Text style={styles.summaryValue}>{report.moment_count}</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <Text style={styles.summaryLabel}>CHOICES</Text>
          <Text style={styles.summaryValue}>{report.option_choices}</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <Text style={styles.summaryLabel}>DIVERGENCES</Text>
          <Text style={styles.summaryValue}>{report.divergence_count}</Text>
        </View>
      </View>

      {/* 4 observation cards */}
      <View style={styles.obsSection}>
        {observations.map((text, i) => (
          <ObservationCard
            key={i}
            index={i}
            label={OBSERVATION_META[i]?.label ?? `Observation ${i + 1}`}
            text={text}
            color={OBSERVATION_META[i]?.color ?? '#9ca3af'}
          />
        ))}
      </View>

      {/* Practitioner strengths & development areas */}
      {report.strengths && report.strengths.length > 0 && (
        <View style={styles.attributeSection}>
          <Text style={styles.attributeLabel}>STRENGTHS</Text>
          <View style={styles.pillRow}>
            {report.strengths.map((s, i) => (
              <View key={i} style={[styles.pill, styles.pillGreen]}>
                <Text style={styles.pillTextGreen}>{s}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {report.development_areas && report.development_areas.length > 0 && (
        <View style={styles.attributeSection}>
          <Text style={styles.attributeLabel}>DEVELOPMENT AREAS</Text>
          <View style={styles.pillRow}>
            {report.development_areas.map((d, i) => (
              <View key={i} style={[styles.pill, styles.pillAmber]}>
                <Text style={styles.pillTextAmber}>{d}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Done */}
      <TouchableOpacity style={styles.doneButton} onPress={handleDone}>
        <Text style={styles.doneText}>Done — New Session</Text>
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
    gap: 14,
    backgroundColor: '#030712',
    padding: 24,
  },
  subText: {
    color: '#6b7280',
    fontSize: 13,
  },
  errorText: {
    color: '#f87171',
    fontSize: 14,
    textAlign: 'center',
  },
  header: {
    gap: 2,
  },
  postSessionTag: {
    fontSize: 9,
    color: '#4b5563',
    fontWeight: '600',
    letterSpacing: 1.2,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#f9fafb',
  },
  subtitle: {
    fontSize: 12,
    color: '#6b7280',
    fontFamily: 'monospace',
  },
  summaryStrip: {
    flexDirection: 'row',
    backgroundColor: '#111827',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    justifyContent: 'space-around',
  },
  summaryItem: {
    alignItems: 'center',
    gap: 3,
  },
  summaryLabel: {
    fontSize: 8,
    color: '#6b7280',
    fontWeight: '600',
    letterSpacing: 0.6,
  },
  summaryValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#f3f4f6',
  },
  summaryDivider: {
    width: 1,
    height: 30,
    backgroundColor: '#1f2937',
  },
  obsSection: {
    gap: 10,
  },
  obsCard: {
    backgroundColor: '#111827',
    borderRadius: 10,
    padding: 14,
    borderLeftWidth: 3,
    gap: 8,
  },
  obsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  obsIcon: {
    fontSize: 14,
    fontWeight: '700',
  },
  obsLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  obsText: {
    fontSize: 14,
    color: '#d1d5db',
    lineHeight: 21,
  },
  attributeSection: {
    gap: 8,
  },
  attributeLabel: {
    fontSize: 9,
    color: '#6b7280',
    fontWeight: '600',
    letterSpacing: 0.8,
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  pill: {
    borderRadius: 20,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  pillGreen: {
    backgroundColor: '#14532d',
  },
  pillAmber: {
    backgroundColor: '#713f12',
  },
  pillTextGreen: {
    color: '#4ade80',
    fontSize: 11,
    fontWeight: '600',
  },
  pillTextAmber: {
    color: '#fde68a',
    fontSize: 11,
    fontWeight: '600',
  },
  doneButton: {
    backgroundColor: '#1f2937',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#374151',
  },
  doneText: {
    color: '#f3f4f6',
    fontSize: 14,
    fontWeight: '700',
  },
});

export default MirrorReportScreen;
