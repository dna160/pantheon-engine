/**
 * BLEManager.ts — Plaud Note Pro BLE connection manager.
 *
 * Uses react-native-ble-plx to connect to the Plaud Note Pro device.
 * Once connected, raw PCM audio bytes are streamed via AudioStreamer.ts
 * to the backend WebSocket → AudioBridge → AudioBuffer.
 *
 * Connection lifecycle:
 *   1. scanForDevice() — scan for Plaud Note Pro by service UUID / name
 *   2. connect(deviceId) — establish GATT connection
 *   3. startAudioStream() — subscribe to audio characteristic notifications
 *   4. stopAudioStream() + disconnect() — cleanup on session end
 *
 * Plaud Note Pro BLE protocol:
 *   - Service UUID: configured in PLAUD_SERVICE_UUID
 *   - Audio characteristic: PLAUD_AUDIO_CHAR_UUID
 *   - MTU: 512 bytes (negotiated on connect)
 *   - Sample rate: 16kHz, mono, PCM16
 */

// NOTE: react-native-ble-plx is imported dynamically at runtime.
// Tests run in Jest (no native modules) — guard all BLE calls.

export type BLEConnectionState =
  | 'idle'
  | 'scanning'
  | 'connecting'
  | 'connected'
  | 'streaming'
  | 'disconnected'
  | 'error';

export interface BLEDevice {
  id: string;
  name: string | null;
  rssi: number | null;
}

type AudioChunkCallback = (bytes: Uint8Array) => void;
type StateChangeCallback = (state: BLEConnectionState) => void;

// Plaud Note Pro BLE UUIDs (update when hardware spec confirmed)
const PLAUD_SERVICE_UUID = '0000FFE0-0000-1000-8000-00805F9B34FB';
const PLAUD_AUDIO_CHAR_UUID = '0000FFE1-0000-1000-8000-00805F9B34FB';
const PLAUD_DEVICE_NAME_PREFIX = 'PLAUD';

// ================================================================== //
//  BLE MANAGER                                                         //
// ================================================================== //

export class BLEManager {
  private manager: any = null;
  private connectedDevice: any = null;
  private connectionState: BLEConnectionState = 'idle';
  private onAudioChunk: AudioChunkCallback | null = null;
  private onStateChange: StateChangeCallback | null = null;
  private audioSubscription: any = null;

  constructor() {
    this._initManager();
  }

  private _initManager(): void {
    try {
      const { BleManager } = require('react-native-ble-plx');
      this.manager = new BleManager();
    } catch {
      // Not available in test / web environment — stub mode
      this.manager = null;
    }
  }

  /**
   * Register callback for incoming audio bytes.
   * Called on every BLE notification (~50ms intervals at 16kHz).
   */
  onAudio(callback: AudioChunkCallback): void {
    this.onAudioChunk = callback;
  }

  /**
   * Register callback for connection state changes.
   */
  onState(callback: StateChangeCallback): void {
    this.onStateChange = callback;
  }

  /**
   * Scan for Plaud Note Pro devices.
   * Calls back with discovered devices. Call stopScan() or connect() to stop.
   */
  async scanForDevice(
    onDiscovered: (device: BLEDevice) => void,
    timeoutMs: number = 10_000,
  ): Promise<void> {
    if (!this.manager) {
      return;
    }

    this._setState('scanning');

    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        this.manager.stopDeviceScan();
        this._setState('idle');
        resolve();
      }, timeoutMs);

      this.manager.startDeviceScan(
        [PLAUD_SERVICE_UUID],
        null,
        (error: Error | null, device: any) => {
          if (error) {
            clearTimeout(timer);
            this._setState('error');
            resolve();
            return;
          }
          if (device?.name?.startsWith(PLAUD_DEVICE_NAME_PREFIX)) {
            onDiscovered({ id: device.id, name: device.name, rssi: device.rssi });
          }
        },
      );
    });
  }

  /**
   * Connect to a specific device by ID.
   * Negotiates MTU 512 for larger audio packets.
   */
  async connect(deviceId: string): Promise<boolean> {
    if (!this.manager) return false;

    this._setState('connecting');
    this.manager.stopDeviceScan();

    try {
      const device = await this.manager.connectToDevice(deviceId);
      await device.discoverAllServicesAndCharacteristics();
      await device.requestMTU(512);
      this.connectedDevice = device;
      this._setState('connected');
      return true;
    } catch {
      this._setState('error');
      return false;
    }
  }

  /**
   * Subscribe to audio characteristic notifications.
   * Each notification fires onAudioChunk callback with raw PCM bytes.
   */
  startAudioStream(): boolean {
    if (!this.connectedDevice || !this.onAudioChunk) return false;

    try {
      this.audioSubscription = this.connectedDevice.monitorCharacteristicForService(
        PLAUD_SERVICE_UUID,
        PLAUD_AUDIO_CHAR_UUID,
        (error: Error | null, characteristic: any) => {
          if (error || !characteristic?.value) return;
          // characteristic.value is base64 — decode to bytes
          const bytes = this._base64ToUint8Array(characteristic.value);
          this.onAudioChunk?.(bytes);
        },
      );

      this._setState('streaming');
      return true;
    } catch {
      this._setState('error');
      return false;
    }
  }

  /**
   * Stop audio stream and disconnect.
   */
  async disconnect(): Promise<void> {
    this.audioSubscription?.remove();
    this.audioSubscription = null;

    if (this.connectedDevice) {
      try {
        await this.connectedDevice.cancelConnection();
      } catch {
        // Ignore disconnect errors
      }
      this.connectedDevice = null;
    }

    this._setState('disconnected');
  }

  get state(): BLEConnectionState {
    return this.connectionState;
  }

  get isStreaming(): boolean {
    return this.connectionState === 'streaming';
  }

  private _setState(state: BLEConnectionState): void {
    this.connectionState = state;
    this.onStateChange?.(state);
  }

  private _base64ToUint8Array(base64: string): Uint8Array {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
  }
}
