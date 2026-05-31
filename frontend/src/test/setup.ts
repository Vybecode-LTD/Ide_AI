import '@testing-library/jest-dom/vitest'

/**
 * jsdom in this environment does not expose a global `localStorage`, which the
 * persisted Zustand stores (`zustand/middleware` → `persist`) require the moment
 * `setState` runs. Provide a minimal in-memory Storage so persisted stores are
 * testable. Installed only when missing, so a real jsdom/CI storage wins.
 */
class MemoryStorage implements Storage {
  private store = new Map<string, string>()
  get length() {
    return this.store.size
  }
  clear() {
    this.store.clear()
  }
  getItem(key: string) {
    return this.store.has(key) ? (this.store.get(key) as string) : null
  }
  setItem(key: string, value: string) {
    this.store.set(key, String(value))
  }
  removeItem(key: string) {
    this.store.delete(key)
  }
  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null
  }
}

if (typeof globalThis.localStorage === 'undefined') {
  Object.defineProperty(globalThis, 'localStorage', { value: new MemoryStorage(), writable: true })
}
if (typeof globalThis.sessionStorage === 'undefined') {
  Object.defineProperty(globalThis, 'sessionStorage', { value: new MemoryStorage(), writable: true })
}
