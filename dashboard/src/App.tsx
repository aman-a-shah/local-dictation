import { useEffect, useState } from "react";
import { Logo, Button, Waveform } from "@voca/ui";
import { api, nativeReady } from "./api";
import type { Stats, Transcription, Settings, Meta, UpdateInfo } from "./api";

// Small inline check used on the dark hero strip (gold, paired with text).
function Check() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

type View = "overview" | "history" | "settings";

export function App() {
  const [view, setView] = useState<View>("overview");
  const [meta, setMeta] = useState<Meta | null>(null);
  // Assume the real bridge until told otherwise, so the app never flashes the
  // "preview" badge while pywebview is still wiring up its js_api.
  const [native, setNative] = useState(true);

  useEffect(() => {
    // `api` now awaits the bridge internally, so a single call is enough — no
    // hand-rolled retry needed (and the old retry never actually re-ran).
    api.get_meta().then(setMeta).catch(() => {});
    nativeReady.then(setNative);
  }, []);

  return (
    <div className="app">
      <aside className="side">
        <div className="side__brand">
          <Logo size={22} appMark />
        </div>
        <nav className="nav" aria-label="Views">
          <NavItem icon="◳" label="Overview" active={view === "overview"} onClick={() => setView("overview")} />
          <NavItem icon="≣" label="History" active={view === "history"} onClick={() => setView("history")} />
          <NavItem icon="⚙" label="Settings" active={view === "settings"} onClick={() => setView("settings")} />
        </nav>
        <div className="side__foot">
          <span className="side__priv">on-device</span>
          <span>v{meta?.version ?? "—"}</span>
          <span>{meta ? `${meta.platform} · ${meta.arch}` : ""}</span>
          {!native && <span style={{ color: "var(--accent)" }}>preview (mock data)</span>}
        </div>
      </aside>

      <div className="main">
        {view === "overview" && <Overview meta={meta} onSeeAll={() => setView("history")} />}
        {view === "history" && <History />}
        {view === "settings" && <SettingsView meta={meta} />}
      </div>
    </div>
  );
}

function NavItem({ icon, label, active, onClick }: { icon: string; label: string; active: boolean; onClick: () => void }) {
  return (
    <button aria-current={active} onClick={onClick}>
      <span className="nav__icon" aria-hidden="true">{icon}</span>
      {label}
    </button>
  );
}

// ---- Formatters -----------------------------------------------------------
const nf = new Intl.NumberFormat();
function fmtDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}
function fmtRelative(ts: number): string {
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  const d = Math.floor(diff / 86400);
  if (d < 7) return `${d}d ago`;
  return new Date(ts * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// ---- Overview -------------------------------------------------------------
function Overview({ meta, onSeeAll }: { meta: Meta | null; onSeeAll: () => void }) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<Transcription[]>([]);
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    api.get_stats().then(setStats).catch(() => {});
    api.get_recent(5, 0).then(setRecent).catch(() => {});
    api.check_update().then(setUpdate).catch(() => {});
  }, []);

  const maxDay = stats ? Math.max(1, ...stats.daily.map((d) => d.words)) : 1;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <>
      <section className="hero fade-up" aria-label="Voca">
        <div className="hero__grid" aria-hidden="true" />
        <div className="hero__copy">
          <div className="hero__brand">
            <Logo size={30} appMark withWordmark={false} />
            <span className="hero__title">Voca</span>
          </div>
          <p className="hero__sub">
            Push-to-talk voice typing that runs entirely on your machine. Hold {meta?.hotkey_label ?? "your key"},
            speak, release.
          </p>
          <div className="hero__chips">
            <span className="hero__chip"><Check /> 100% on-device</span>
            <span className="hero__chip"><Check /> No account</span>
            <span className="hero__chip"><Check /> Stays on this device</span>
          </div>
        </div>
        <div className="hero__wave">
          <Waveform mode="idle" height={104} bars={40} />
        </div>
      </section>

      {update?.available && (
        <div className="update-banner">
          <span>
            Update available — <strong>v{update.latest}</strong>
          </span>
          {update.url && (
            <Button
              disabled={updating}
              onClick={() => {
                setUpdating(true);
                // One-click: Python downloads the installer and hands it to the
                // OS. If the bridge fails for any reason, fall back to the URL.
                api
                  .download_update(update.url!)
                  .then((r) => {
                    if (!r.ok && update.url) window.location.href = update.url;
                  })
                  .catch(() => {
                    if (update.url) window.location.href = update.url;
                  })
                  .finally(() => setUpdating(false));
              }}
            >
              {updating ? "Downloading…" : "Get it"}
            </Button>
          )}
        </div>
      )}

      <div className="stat-band">
        <div className="stat stat--feature">
          <div className="stat__num stat__num--gold">
            {stats ? nf.format(stats.words) : "—"}
          </div>
          <div className="stat__label">words transcribed</div>
          <div className="stat__hint">{stats ? `across ${nf.format(stats.sessions)} sessions` : ""}</div>
        </div>
        <div className="stat">
          <div className="stat__num">{stats ? fmtDuration(stats.time_saved_seconds) : "—"}</div>
          <div className="stat__label">time saved</div>
          <div className="stat__hint">vs. typing at 40 wpm</div>
        </div>
        <div className="stat">
          <div className="stat__num">{stats ? nf.format(stats.streak_days) : "—"}</div>
          <div className="stat__label">day streak</div>
          <div className="stat__hint">consecutive days</div>
        </div>
        <div className="stat">
          <div className="stat__num">{stats ? fmtDuration(stats.audio_seconds) : "—"}</div>
          <div className="stat__label">spoken</div>
          <div className="stat__hint">{stats ? `${fmtDuration(stats.compute_seconds)} computing` : ""}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel__head">
          <h2>Activity</h2>
          <span>words / day</span>
        </div>
        <div className="chart">
          {(stats?.daily ?? []).map((d, i) => (
            <div
              key={i}
              className={`chart__bar${d.day === today ? " chart__bar--today" : ""}`}
              style={{ height: `${(d.words / maxDay) * 100}%` }}
              title={`${d.day}: ${nf.format(d.words)} words`}
            />
          ))}
        </div>
        {stats && stats.daily.length > 1 && (
          <div className="chart__labels">
            <span>{stats.daily[0].day.slice(5)}</span>
            <span>{stats.daily[stats.daily.length - 1].day.slice(5)}</span>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel__head">
          <h2>Recent</h2>
          <button className="see-all" onClick={onSeeAll}>see all →</button>
        </div>
        {recent.length === 0 ? (
          <p className="empty-note">
            No transcriptions yet. Hold {meta?.hotkey_label ?? "your key"} and speak.
          </p>
        ) : (
          recent.map((t) => (
            <div className="entry" key={t.id}>
              <div className="entry__body">
                <div className="entry__text">{t.text}</div>
                <div className="entry__meta">
                  <span>{fmtRelative(t.ts)}</span>
                  <span className="entry__words">{t.words} words</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );
}

// ---- History --------------------------------------------------------------
function History() {
  const [items, setItems] = useState<Transcription[]>([]);
  const [query, setQuery] = useState("");

  const refresh = () => {
    const p = query.trim() ? api.search(query, 200) : api.get_recent(200, 0);
    p.then(setItems).catch(() => {});
  };
  useEffect(refresh, [query]);

  const del = (id: number) => {
    api.delete_item(id).then(() => setItems((xs) => xs.filter((x) => x.id !== id)));
  };
  const copy = (id: number) => api.copy_text(id);
  const clearAll = () => {
    if (confirm("Delete all transcription history? This can't be undone.")) {
      api.clear_history().then(() => setItems([]));
    }
  };

  return (
    <>
      <header className="view-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1>History</h1>
          <p>{items.length} transcription{items.length === 1 ? "" : "s"}</p>
        </div>
        {items.length > 0 && (
          <button className="icon-btn icon-btn--danger" onClick={clearAll}>Clear all</button>
        )}
      </header>

      <input
        className="search"
        placeholder="Search transcriptions…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {items.length === 0 ? (
        <div className="empty-state">
          <div className="wave-wrap">
            <Waveform mode="idle" height={80} bars={32} />
          </div>
          <p>{query ? "No matches." : "Nothing here yet — your transcriptions will appear as you dictate."}</p>
        </div>
      ) : (
        items.map((t) => (
          <div className="entry" key={t.id}>
            <div className="entry__body">
              <div className="entry__text">{t.text}</div>
              <div className="entry__meta">
                <span>{fmtRelative(t.ts)}</span>
                <span className="entry__words">{t.words} words</span>
                <span>{t.duration_s.toFixed(1)}s audio</span>
                {t.lang && <span>{t.lang}</span>}
              </div>
            </div>
            <div className="entry__actions">
              <button className="icon-btn" onClick={() => copy(t.id)}>copy</button>
              <button className="icon-btn icon-btn--danger" onClick={() => del(t.id)}>delete</button>
            </div>
          </div>
        ))
      )}
    </>
  );
}

// ---- Settings -------------------------------------------------------------
const LANGS = [
  ["en", "English"], ["auto", "Auto-detect"], ["es", "Spanish"], ["fr", "French"],
  ["de", "German"], ["it", "Italian"], ["pt", "Portuguese"], ["nl", "Dutch"],
  ["zh", "Chinese"], ["ja", "Japanese"], ["ko", "Korean"], ["hi", "Hindi"],
];
const KEYS = [
  ["ctrl_l", "Left Ctrl"], ["ctrl_r", "Right Ctrl"], ["alt_r", "Right Alt"],
  ["alt_l", "Left Alt"], ["f8", "F8"], ["f9", "F9"],
];

function SettingsView({ meta }: { meta: Meta | null }) {
  const [s, setS] = useState<Settings | null>(null);
  const [savedNote, setSavedNote] = useState(false);
  const isMac = meta?.platform === "Darwin";

  useEffect(() => {
    api.get_settings().then(setS).catch(() => {});
  }, []);

  const update = (patch: Partial<Settings>) => {
    if (!s) return;
    const next = { ...s, ...patch };
    setS(next);
    api.set_settings(patch).catch(() => {});
    setSavedNote(true);
  };

  if (!s) return <div className="view-head"><h1>Settings</h1></div>;

  return (
    <>
      <header className="view-head">
        <h1>Settings</h1>
        <p>Changes are saved instantly. Some apply on next launch.</p>
      </header>

      <div className="settings-card">
        <Row label="Push-to-talk key" desc={isMac ? "macOS uses the fn (globe) key by default." : "Hold this key to dictate."}>
          {isMac ? (
            <span className="ld-kbd">fn</span>
          ) : (
            <select value={s.hotkey} onChange={(e) => update({ hotkey: e.target.value })}>
              {KEYS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          )}
        </Row>

        <Row label="Language" desc="Pin a language to skip detection (slightly faster).">
          <select value={s.language} onChange={(e) => update({ language: e.target.value })}>
            {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </Row>

        <Toggle label="Smart formatting" desc="Turn spoken enumerations into clean numbered or bulleted lists." checked={s.polish} onChange={(v) => update({ polish: v })} />
        <Toggle label="Trailing space" desc="Add a space after each insert for continuous dictation." checked={s.append_space} onChange={(v) => update({ append_space: v })} />
        <Toggle label="Restore clipboard" desc="Put your previous clipboard back after pasting." checked={s.restore_clipboard} onChange={(v) => update({ restore_clipboard: v })} />
        <Toggle label="Sound cues" desc="Soft sounds when listening starts and text is inserted." checked={s.sound_feedback} onChange={(v) => update({ sound_feedback: v })} />
        <Toggle label="Run at login" desc="Start Voca automatically when you sign in." checked={s.run_at_login} onChange={(v) => update({ run_at_login: v })} />
        <Toggle label="Save history" desc="Keep a local record of transcriptions for this dashboard." checked={s.save_history} onChange={(v) => update({ save_history: v })} />
      </div>

      {savedNote && (
        <p className="restart-note">Saved. Key, language and model changes take effect after you quit and relaunch.</p>
      )}
    </>
  );
}

function Row({ label, desc, children }: { label: string; desc?: string; children: React.ReactNode }) {
  return (
    <div className="setting">
      <div>
        <div className="setting__label">{label}</div>
        {desc && <div className="setting__desc">{desc}</div>}
      </div>
      {children}
    </div>
  );
}

function Toggle({ label, desc, checked, onChange }: { label: string; desc?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <Row label={label} desc={desc}>
      <button className="toggle" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)} />
    </Row>
  );
}
