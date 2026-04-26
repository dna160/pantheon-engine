/**
 * DialogOptions.tsx — 3 dialog options with probability bars.
 *
 * Displays the 3 genome-calibrated + SLM-adapted dialog options.
 * Each option shows:
 *   - core_approach (strategy label)
 *   - base_language (full text — practitioner reads this)
 *   - probability bar (visual confidence)
 *   - trigger_phrase (3-word shorthand)
 *
 * Options are sorted by base_probability descending.
 * Tapping an option fires onSelect (logged to session_logger via SessionService).
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import type { DialogOption } from '../types';

interface SelectionState {
  option_a: DialogOption;
  option_b: DialogOption;
  option_c: DialogOption;
  was_adapted: boolean;
  is_cache_fallback: boolean;
}

interface Props {
  options: SelectionState;
  onSelect: (key: 'option_a' | 'option_b' | 'option_c') => void;
  selectedKey?: 'option_a' | 'option_b' | 'option_c' | null;
}

type OptionKey = 'option_a' | 'option_b' | 'option_c';

function probColor(prob: number): string {
  if (prob >= 70) return '#22c55e';
  if (prob >= 50) return '#f59e0b';
  return '#6b7280';
}

const DialogOptions: React.FC<Props> = ({ options, onSelect, selectedKey }) => {
  const entries: [OptionKey, DialogOption][] = [
    ['option_a', options.option_a],
    ['option_b', options.option_b],
    ['option_c', options.option_c],
  ];

  // Sort by probability descending
  const sorted = [...entries].sort(([, a], [, b]) => b.base_probability - a.base_probability);

  return (
    <View style={styles.container}>
      {/* Adaptation indicator */}
      {options.was_adapted && (
        <Text style={styles.adaptedBadge}>✦ SLM-adapted to current state</Text>
      )}
      {options.is_cache_fallback && (
        <Text style={styles.fallbackBadge}>⚠ Using generic fallback options</Text>
      )}

      {sorted.map(([key, option], index) => {
        const isSelected = selectedKey === key;
        const isTop = index === 0;

        return (
          <TouchableOpacity
            key={key}
            style={[
              styles.card,
              isTop && styles.topCard,
              isSelected && styles.selectedCard,
            ]}
            onPress={() => onSelect(key)}
            activeOpacity={0.8}
          >
            {/* Header row */}
            <View style={styles.cardHeader}>
              <Text style={styles.approach}>{option.core_approach}</Text>
              <View style={styles.probContainer}>
                <Text style={[styles.prob, { color: probColor(option.base_probability) }]}>
                  {option.base_probability}%
                </Text>
              </View>
            </View>

            {/* Probability bar */}
            <View style={styles.probTrack}>
              <View
                style={[
                  styles.probFill,
                  {
                    width: `${option.base_probability}%`,
                    backgroundColor: probColor(option.base_probability),
                  },
                ]}
              />
            </View>

            {/* Base language */}
            <Text style={styles.language}>{option.base_language}</Text>

            {/* Trigger phrase */}
            <Text style={styles.trigger}>"{option.trigger_phrase}"</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    gap: 8,
  },
  adaptedBadge: {
    fontSize: 10,
    color: '#6366f1',
    fontStyle: 'italic',
    marginBottom: 2,
  },
  fallbackBadge: {
    fontSize: 10,
    color: '#f59e0b',
    fontStyle: 'italic',
    marginBottom: 2,
  },
  card: {
    backgroundColor: '#111827',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#1f2937',
    gap: 6,
  },
  topCard: {
    borderColor: '#374151',
  },
  selectedCard: {
    borderColor: '#6366f1',
    backgroundColor: '#1e1b4b',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  approach: {
    fontSize: 11,
    fontWeight: '600',
    color: '#9ca3af',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    flex: 1,
  },
  probContainer: {
    alignItems: 'flex-end',
  },
  prob: {
    fontSize: 13,
    fontWeight: '700',
  },
  probTrack: {
    height: 3,
    backgroundColor: '#1f2937',
    borderRadius: 2,
    overflow: 'hidden',
  },
  probFill: {
    height: '100%',
    borderRadius: 2,
  },
  language: {
    fontSize: 14,
    color: '#f3f4f6',
    lineHeight: 20,
    fontStyle: 'italic',
  },
  trigger: {
    fontSize: 11,
    color: '#6b7280',
    fontWeight: '600',
  },
});

export default DialogOptions;
