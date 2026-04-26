/**
 * AudioStreamer.ts — Pipes BLE audio bytes to the backend WebSocket.
 *
 * Sits between BLEManager (hardware source) and the backend AudioBridge
 * (consumer). Receives raw PCM bytes from BLEManager.onAudio(), batches
 * them into 1600-byte chunks (50ms @ 16kHz mono PCM16), and sends via
 * WebSocket binary frame to the backend.
 *
 * The backend AudioBridge.receive_bytes() handles everything downstream.
 * This class has no knowledge of audio processing — it is a transport only.
 *
 * Chunk size: 1600 bytes = 50ms × 16kHz × 2 bytes/sample (PCM16 mono)
 */

const CHUNK_SIZE_BYTES = 1600;  // 50ms at 16kHz mono PCM16

export class AudioStreamer {
  private ws: WebSocket | null = null;
  private buffer: Uint8Array = new Uint8Array(0);
  private chunksSent = 0;
  private sessionId: string;
  private baseUrl: string;
  private connected = false;

  constructor(sessionId: string, baseUrl: string = 'ws://localhost:8000') {
    this.sessionId = sessionId;
    this.baseUrl = baseUrl;
  }

  /**
   * Open WebSocket connection to backend AudioBridge endpoint.
   * Must be called before start() — before BLE stream begins.
   */
  async open(): Promise<boolean> {
    const url = `${this.baseUrl}/ws/audio/${this.sessionId}`;

    return new Promise((resolve) => {
      try {
        this.ws = new WebSocket(url);
        this.ws.binaryType = 'arraybuffer';

        this.ws.onopen = () => {
          this.connected = true;
          resolve(true);
        };

        this.ws.onerror = () => {
          this.connected = false;
          resolve(false);
        };

        this.ws.onclose = () => {
          this.connected = false;
        };
      } catch {
        resolve(false);
      }
    });
  }

  /**
   * Receive raw bytes from BLEManager.onAudio().
   * Accumulates into buffer, flushes complete 50ms chunks to WebSocket.
   */
  receiveBytes(bytes: Uint8Array): void {
    if (!this.connected || !this.ws) return;

    // Append to buffer
    const merged = new Uint8Array(this.buffer.length + bytes.length);
    merged.set(this.buffer, 0);
    merged.set(bytes, this.buffer.length);
    this.buffer = merged;

    // Flush complete chunks
    while (this.buffer.length >= CHUNK_SIZE_BYTES) {
      const chunk = this.buffer.slice(0, CHUNK_SIZE_BYTES);
      this.buffer = this.buffer.slice(CHUNK_SIZE_BYTES);
      this._send(chunk);
    }
  }

  /**
   * Flush any remaining buffered bytes and close the WebSocket.
   * Called when session ends or BLE disconnects.
   */
  close(): void {
    // Flush any partial buffer
    if (this.buffer.length > 0 && this.connected && this.ws) {
      this._send(this.buffer);
      this.buffer = new Uint8Array(0);
    }

    this.ws?.close();
    this.ws = null;
    this.connected = false;
  }

  get isConnected(): boolean {
    return this.connected;
  }

  get totalChunksSent(): number {
    return this.chunksSent;
  }

  private _send(chunk: Uint8Array): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(chunk.buffer);
    this.chunksSent += 1;
  }
}
