/**
 * WatchBridge.ts — React Native → WatchOS / WearOS bridge.
 *
 * Uses react-native-watch-connectivity to push HUD state updates
 * to the paired smartwatch (WatchOS on iPhone, WearOS on Android).
 *
 * The watch displays:
 *   - Hook bar score (0–100)
 *   - Close bar score (0–100)
 *   - 3-word trigger phrase (from highest-probability option)
 *   - Trend arrows (rising/falling/stable)
 *
 * Updates are pushed on every full HUD render from the backend.
 * Haptic patterns are translated to watch-specific APIs.
 *
 * This bridge is a one-way push — the watch does not send data back
 * to the phone in v1 (future: option confirmation tap on watch).
 */

type WatchPayload = {
  hook: number;
  close: number;
  trigger: string;
  hook_trend: 'rising' | 'falling' | 'stable';
  close_trend: 'rising' | 'falling' | 'stable';
};

type HapticPattern = 'single' | 'double' | 'long';

// ================================================================== //
//  WATCH BRIDGE                                                        //
// ================================================================== //

export class WatchBridge {
  private watchAPI: any = null;
  private isReachable = false;
  private lastPayload: WatchPayload | null = null;

  constructor() {
    this._initWatchAPI();
  }

  private _initWatchAPI(): void {
    try {
      const watchConnectivity = require('react-native-watch-connectivity');
      this.watchAPI = watchConnectivity;

      // Listen for reachability changes
      this.watchAPI.subscribeToWatchReachability((reachable: boolean) => {
        this.isReachable = reachable;
        // Re-send last payload if watch just became reachable
        if (reachable && this.lastPayload) {
          this._sendToWatch(this.lastPayload);
        }
      });
    } catch {
      // Not available in test / web environment — stub mode
      this.watchAPI = null;
    }
  }

  /**
   * Push bar state + trigger phrase to watch.
   * Called from Zone 2 HUD update cycle.
   */
  updateHUD(payload: WatchPayload): void {
    this.lastPayload = payload;
    if (this.isReachable) {
      this._sendToWatch(payload);
    }
  }

  /**
   * Trigger haptic on watch.
   * Patterns: 'single' (moment change), 'double' (close peak), 'long' (divergence alert).
   */
  haptic(pattern: HapticPattern): void {
    if (!this.watchAPI || !this.isReachable) return;

    try {
      // react-native-watch-connectivity uses sendMessage for haptic commands
      this.watchAPI.sendMessage(
        { type: 'haptic', pattern },
        () => {}, // success
        () => {}, // error — ignore
      );
    } catch {
      // Ignore haptic errors
    }
  }

  /**
   * Clear watch display. Called on session end.
   */
  clear(): void {
    this.updateHUD({
      hook: 0,
      close: 0,
      trigger: '---',
      hook_trend: 'stable',
      close_trend: 'stable',
    });
    this.lastPayload = null;
  }

  get reachable(): boolean {
    return this.isReachable;
  }

  private _sendToWatch(payload: WatchPayload): void {
    if (!this.watchAPI) return;

    try {
      this.watchAPI.updateApplicationContext(payload);
    } catch {
      // Ignore send errors — watch state will sync on next reachability
    }
  }
}
