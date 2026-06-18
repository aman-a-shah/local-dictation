// Bridge to the Python backend (dictate/bridge.py) exposed by pywebview as
// window.pywebview.api. In a plain browser (dev / preview) there's no bridge, so
// we fall back to a mock with sample data — the UI is identical either way.

export type Transcription = {
  id: number;
  ts: number;
  text: string;
  words: number;
  chars: number;
  duration_s: number;
  elapsed_s: number;
  model: string;
  lang: string;
};

export type Stats = {
  sessions: number;
  words: number;
  chars: number;
  audio_seconds: number;
  compute_seconds: number;
  time_saved_seconds: number;
  first_ts: number | null;
  last_ts: number | null;
  daily: { day: string; words: number; sessions: number }[];
  streak_days: number;
};

export type Settings = {
  language: string;
  hotkey: string;
  polish: boolean;
  list_style: string;
  sound_feedback: boolean;
  append_space: boolean;
  restore_clipboard: boolean;
  save_history: boolean;
  run_at_login: boolean;
};

export type Meta = {
  version: string;
  platform: string;
  arch: string;
  hotkey_label: string;
};

export type UpdateInfo = {
  available: boolean;
  latest?: string;
  url?: string;
  notes?: string;
  error?: string;
};

type Bridge = {
  get_stats(): Promise<Stats>;
  get_recent(limit: number, offset: number): Promise<Transcription[]>;
  search(query: string, limit: number): Promise<Transcription[]>;
  delete_item(id: number): Promise<boolean>;
  clear_history(): Promise<boolean>;
  copy_text(id: number): Promise<string>;
  get_settings(): Promise<Settings>;
  set_settings(values: Partial<Settings>): Promise<Settings>;
  get_meta(): Promise<Meta>;
  check_update(): Promise<UpdateInfo>;
};

export const isNative = typeof window !== "undefined" && !!(window as any).pywebview?.api;

function nativeApi(): Bridge {
  return (window as any).pywebview.api as Bridge;
}

// ---- Mock (browser preview) ----------------------------------------------
const SAMPLES = [
  "Let's ship the cross-platform build this week and write the release notes.",
  "Remind me to follow up with the design team about the dashboard spacing.",
  "My grocery list is milk, eggs, sourdough, and a bag of coffee.",
  "The quarterly numbers look strong, especially retention in the new cohort.",
  "Draft a short reply: thanks for the thoughtful feedback, I'll incorporate it.",
  "First, set up the venv. Second, install requirements. Third, run the app.",
  "Push to talk is genuinely faster than typing once you build the muscle memory.",
];

function mockRecent(n: number, offset = 0): Transcription[] {
  const now = Date.now() / 1000;
  return Array.from({ length: n }, (_, i) => {
    const k = i + offset;
    const text = SAMPLES[k % SAMPLES.length];
    return {
      id: 1000 - k,
      ts: now - k * 7300 - 400,
      text,
      words: text.split(/\s+/).length,
      chars: text.length,
      duration_s: 2 + (k % 5),
      elapsed_s: 0.2 + (k % 3) * 0.1,
      model: "whisper-large-v3-turbo",
      lang: "en",
    };
  });
}

function mockStats(): Stats {
  const recent = mockRecent(40);
  const words = recent.reduce((a, b) => a + b.words, 0) + 8200;
  const days = Array.from({ length: 14 }, (_, i) => {
    const d = new Date(Date.now() - (13 - i) * 86400000);
    return {
      day: d.toISOString().slice(0, 10),
      words: Math.round(120 + Math.abs(Math.sin(i * 1.3)) * 640),
      sessions: 3 + (i % 6),
    };
  });
  return {
    sessions: 612,
    words,
    chars: words * 5.4,
    audio_seconds: 9400,
    compute_seconds: 720,
    time_saved_seconds: (words / 40) * 60,
    first_ts: Date.now() / 1000 - 86400 * 60,
    last_ts: Date.now() / 1000 - 400,
    daily: days,
    streak_days: 9,
  };
}

let mockState = {
  history: mockRecent(40),
  settings: {
    language: "en",
    hotkey: "ctrl_l",
    polish: true,
    list_style: "numbered",
    sound_feedback: true,
    append_space: true,
    restore_clipboard: true,
    save_history: true,
    run_at_login: false,
  } as Settings,
};

const mock: Bridge = {
  async get_stats() {
    return mockStats();
  },
  async get_recent(limit, offset) {
    return mockState.history.slice(offset, offset + limit);
  },
  async search(query, limit) {
    const q = query.toLowerCase();
    return mockState.history.filter((t) => t.text.toLowerCase().includes(q)).slice(0, limit);
  },
  async delete_item(id) {
    mockState.history = mockState.history.filter((t) => t.id !== id);
    return true;
  },
  async clear_history() {
    mockState.history = [];
    return true;
  },
  async copy_text(id) {
    const t = mockState.history.find((x) => x.id === id);
    if (t) navigator.clipboard?.writeText(t.text).catch(() => {});
    return t?.text ?? "";
  },
  async get_settings() {
    return mockState.settings;
  },
  async set_settings(values) {
    mockState.settings = { ...mockState.settings, ...values };
    return mockState.settings;
  },
  async get_meta() {
    return { version: "1.0.0", platform: "Preview", arch: "browser", hotkey_label: "Left Ctrl" };
  },
  async check_update() {
    return { available: false };
  },
};

export const api: Bridge = isNative ? nativeApi() : mock;
