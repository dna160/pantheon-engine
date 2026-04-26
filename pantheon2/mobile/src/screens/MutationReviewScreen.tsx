/**
 * MutationReviewScreen.tsx — Post-session genome mutation review.
 *
 * Zone 3: practitioner confirms or dismisses each mutation candidate
 * produced by SessionAnalyzer. No automatic genome writes.
 *
 * Per PRD CLAUDE.md mutation gate:
 *   Human must confirm each candidate. No bypass. No admin path.
 *
 * Per FILE_TREE.md mutation_review_screen.py equivalent:
 *   - Loads candidates from SessionService.getAnalysis()
 *   - Shows each MutationCandidate: trait, direction, strength, rationale
 *   - CONFIRM → respondToMutation('confirm')
 *   - DISMISS → respondToMutation('dismiss')
 *   - Navigates to MirrorReport when all candidates are resolved
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList, MutationReviewPayload, MutationCandidate } from '../types';
import SessionService from '../services/SessionService';

type Props = NativeStackScreenProps<RootStackParamList, 'MutationReview'>;

type Resolution = 'confirm' | 'dismiss' | null;

const STRENGTH_COLOR: Record<string, string> = {
  STRONG:   '#ef4444',
  MODERATE: '#f59e0b',
  WEAK:     '#6b7280',
};

const DIRECTION_ICON: Record<string, string> = {
  increase: '↑',
  decrease: '↓',
  recalibrate: '⟳',
};

const MutationReviewScreen: React.FC<Props> = ({ navigation, route }) => {
  const { sessionId } = route.params;

  const [loading, setLoading] = useState(true);
  const [payload, setPayload] = useState<MutationReviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resolutions, setResolutions] = useState<Map<string, Resolution>>(new Map());
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await SessionService.getAnalysis(sessionId);
        if (!cancelled) {
          setPayload(data);
          setLoading(false);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'Failed to load analysis';
          setError(msg);
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  const candidates: MutationCandidate[] = payload?.mutation_candidates ?? [];
  const allResolved = candidates.length > 0 &&
    candidates.every(c => resolutions.get(c.candidate_id) !== null &&
      resolutions.get(c.candidate_id) !== undefined);

  const handleRespond = useCallback(
    async (candidateId: string, response: 'confirm' | 'dismiss') => {
      setResolutions(prev => new Map(prev).set(candidateId, response));
      try {
        await SessionService.respondToMutation(sessionId, candidateId, response);
      } catch {
        // UI is optimistic; server call is best-effort
      }
    },
    [sessionId],
  );

  const handleFinish = useCallback(async () => {
    setSubmitting(true);
    navigation.replace('MirrorReport', { sessionId });
  }, [navigation, sessionId]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.subText}>Analyzing session…</Text>
      </View>
    );
  }

  if (error || !payload) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>⚠ {error ?? 'Analysis unavailable'}</Text>
        <TouchableOpacity
          style={styles.skipButton}
          onPress={() => navigation.replace('MirrorReport', { sessionId })}
        >
          <Text style={styles.skipText}>Skip to Mirror Report</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (candidates.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.noCandidatesText}>No genome mutations flagged this session.</Text>
        <TouchableOpacity
          style={styles.continueButton}
          onPress={() => navigation.replace('MirrorReport', { sessionId })}
        >
          <Text style={styles.continueText}>Continue to Mirror Report</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.intro}>
          {candidates.length} genome mutation{candidates.length !== 1 ? 's' : ''} flagged.
          Review and confirm or dismiss each.
        </Text>

        {candidates.map((candidate) => {
          const res = resolutions.get(candidate.candidate_id);
          const isConfirmed = res === 'confirm';
          const isDismissed = res === 'dismiss';
          const strengthColor = STRENGTH_COLOR[candidate.strength] ?? '#6b7280';
          const dirIcon = DIRECTION_ICON[candidate.direction] ?? '→';

          return (
            <View
              key={candidate.candidate_id}
              style={[
                styles.card,
                isConfirmed && styles.cardConfirmed,
                isDismissed && styles.cardDismissed,
              ]}
            >
              {/* Trait header */}
              <View style={styles.cardHeader}>
                <Text style={[styles.dirArrow, { color: strengthColor }]}>{dirIcon}</Text>
                <Text style={styles.traitName}>{candidate.trait_name}</Text>
                <View style={[styles.strengthBadge, { backgroundColor: strengthColor + '22' }]}>
                  <Text style={[styles.strengthText, { color: strengthColor }]}>
                    {candidate.strength}
                  </Text>
                </View>
              </View>

              {/* Direction */}
              <Text style={styles.direction}>
                Direction: <Text style={{ color: '#d1d5db' }}>{candidate.direction}</Text>
              </Text>

              {/* Rationale */}
              <Text style={styles.rationale}>{candidate.rationale}</Text>

              {/* Coherence tension flag */}
              {candidate.is_coherence_tension && (
                <View style={styles.tensionBadge}>
                  <Text style={styles.tensionText}>⚠ Coherence tension — verify carefully</Text>
                </View>
              )}

              {/* Observation count */}
              <Text style={styles.obsCount}>
                {candidate.observation_count} observation{candidate.observation_count !== 1 ? 's' : ''}
              </Text>

              {/* Action buttons — only if not yet resolved */}
              {!res && (
                <View style={styles.actionRow}>
                  <TouchableOpacity
                    style={styles.confirmButton}
                    onPress={() => handleRespond(candidate.candidate_id, 'confirm')}
                  >
                    <Text style={styles.confirmText}>✓ CONFIRM</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.dismissButton}
                    onPress={() => handleRespond(candidate.candidate_id, 'dismiss')}
                  >
                    <Text style={styles.dismissText}>✗ DISMISS</Text>
                  </TouchableOpacity>
                </View>
              )}

              {/* Resolution badge */}
              {isConfirmed && (
                <View style={styles.resolvedBadge}>
                  <Text style={styles.resolvedConfirmed}>✓ Confirmed — genome will update</Text>
                </View>
              )}
              {isDismissed && (
                <View style={styles.resolvedBadge}>
                  <Text style={styles.resolvedDismissed}>✗ Dismissed — no change</Text>
                </View>
              )}
            </View>
          );
        })}
      </ScrollView>

      {/* Finish button */}
      <View style={styles.bottomBar}>
        <TouchableOpacity
          style={[styles.finishButton, !allResolved && styles.finishButtonDisabled]}
          onPress={handleFinish}
          disabled={!allResolved || submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#030712" />
          ) : (
            <Text style={[styles.finishText, !allResolved && styles.finishTextDisabled]}>
              {allResolved ? 'View Mirror Report →' : `${candidates.length - resolutions.size} remaining`}
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#030712',
  },
  content: {
    padding: 16,
    gap: 12,
    paddingBottom: 90,
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
  noCandidatesText: {
    color: '#9ca3af',
    fontSize: 15,
    textAlign: 'center',
  },
  skipButton: {
    backgroundColor: '#1f2937',
    borderRadius: 8,
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  skipText: {
    color: '#9ca3af',
    fontSize: 13,
  },
  continueButton: {
    backgroundColor: '#6366f1',
    borderRadius: 10,
    paddingHorizontal: 24,
    paddingVertical: 12,
  },
  continueText: {
    color: '#f9fafb',
    fontWeight: '700',
    fontSize: 14,
  },
  intro: {
    fontSize: 13,
    color: '#9ca3af',
    lineHeight: 20,
  },
  card: {
    backgroundColor: '#111827',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#1f2937',
    padding: 14,
    gap: 8,
  },
  cardConfirmed: {
    borderColor: '#16a34a',
    backgroundColor: '#052e16',
  },
  cardDismissed: {
    borderColor: '#374151',
    opacity: 0.6,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  dirArrow: {
    fontSize: 18,
    fontWeight: '700',
  },
  traitName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#f3f4f6',
    flex: 1,
  },
  strengthBadge: {
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  strengthText: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  direction: {
    fontSize: 12,
    color: '#6b7280',
  },
  rationale: {
    fontSize: 13,
    color: '#d1d5db',
    lineHeight: 19,
  },
  tensionBadge: {
    backgroundColor: '#78350f',
    borderRadius: 6,
    padding: 8,
  },
  tensionText: {
    color: '#fde68a',
    fontSize: 11,
    fontStyle: 'italic',
  },
  obsCount: {
    fontSize: 10,
    color: '#6b7280',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  confirmButton: {
    flex: 1,
    backgroundColor: '#14532d',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#16a34a',
  },
  confirmText: {
    color: '#4ade80',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  dismissButton: {
    flex: 1,
    backgroundColor: '#1f2937',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#374151',
  },
  dismissText: {
    color: '#9ca3af',
    fontSize: 12,
    fontWeight: '600',
  },
  resolvedBadge: {
    paddingVertical: 6,
    alignItems: 'center',
  },
  resolvedConfirmed: {
    color: '#4ade80',
    fontSize: 12,
    fontWeight: '600',
  },
  resolvedDismissed: {
    color: '#6b7280',
    fontSize: 12,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#111827',
    borderTopWidth: 1,
    borderTopColor: '#1f2937',
    padding: 12,
  },
  finishButton: {
    backgroundColor: '#6366f1',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  finishButtonDisabled: {
    backgroundColor: '#1f2937',
  },
  finishText: {
    color: '#f9fafb',
    fontSize: 15,
    fontWeight: '700',
  },
  finishTextDisabled: {
    color: '#4b5563',
  },
});

export default MutationReviewScreen;
