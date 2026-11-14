// Presenter controls and transparent integration status; local controls are never real LD flags.
import { useEffect, useState } from "react";
import { X, SlidersHorizontal, RotateCcw } from "lucide-react";
import { api } from "../services/api";
import ExperimentVisitors from "./ExperimentVisitors";

// DEMO START presenter-controls: Expose diagnostics, local incident simulation, and preview-only release controls.
export default function DemoPanel({
  profiles,
  selected,
  onSelect,
  experience,
  diagnostics,
  onClose,
}) {
  // In live mode, the LD dashboard owns release rules; local controls only simulate incidents.
  const live = experience?.mode === "launchdarkly";
  // SDK initialization and local configuration are not proof that the platform ingested telemetry.
  const instrumented =
    diagnostics.status === "ready"
      ? "SDK initialized"
      : diagnostics.status === "not_configured"
        ? "Needs client-side ID"
        : diagnostics.status;
  const capabilities = [
    [
      "Flag triggers",
      diagnostics.config?.trigger_configured
        ? "Configured · CLI"
        : "Not configured",
    ],
    [
      "Experimentation",
      live ? "Events instrumented · setup in LD" : "Preview only",
    ],
    ["Session replay", instrumented],
    ["Errors, logs & traces", instrumented],
    ["Observability metrics", instrumented],
    [
      "AI Configs",
      diagnostics.config?.ai?.status === "sdk_ready"
        ? "SDK ready · verify generation"
        : (diagnostics.config?.ai?.status ?? "Not connected"),
    ],
  ];
  const [state, setState] = useState(null);
  const [activity, setActivity] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    Promise.all([api.state(), api.activity()])
      .then(([settings, entries]) => {
        setState(settings);
        setActivity(entries);
      })
      .catch((failure) => setError(failure.message));
  }, [experience]);
  async function update(next) {
    setBusy(true);
    setError("");
    try {
      setState(await api.update(next));
      setActivity(await api.activity());
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="demo-panel" aria-label="Presenter controls">
      <header>
        <SlidersHorizontal size={20} />
        <strong>Demo studio</strong>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close demo studio"
        >
          <X size={19} />
        </button>
      </header>
      <div className="panel-body">
        <span className="pill amber">
          {live
            ? experience.integration.connected
              ? "LaunchDarkly connected"
              : "LaunchDarkly reconnecting"
            : "Local preview"}
        </span>
        <h2>One story. Every perspective.</h2>
        <p>
          {live
            ? "Release and targeting are controlled in LaunchDarkly. Changes are streamed to this page without a reload."
            : "Explore the app foundation. These controls run locally; LaunchDarkly is not connected."}
        </p>
        <label htmlFor="profile">Visitor profile</label>
        <select
          id="profile"
          value={selected}
          onChange={(event) => onSelect(event.target.value)}
        >
          {profiles.map((profile) => (
            <option key={profile.key} value={profile.key}>
              {profile.name} · {profile.role}
            </option>
          ))}
        </select>
        <ExperimentVisitors
          profiles={profiles}
          selected={selected}
          onSelect={onSelect}
        />
        {experience && (
          <div className="context-box">
            <code>{experience.profile.key}</code>
            <span>tier: {experience.profile.tier}</span>
            <span>beta_tester: {String(experience.profile.beta_tester)}</span>
            <span>
              experiment_eligible:{" "}
              {String(experience.profile.experiment_eligible)}
            </span>
            <hr />
            <strong>
              {experience.decision.variant === "new"
                ? "New panel"
                : "Existing panel"}
            </strong>
            <span>{experience.decision.reason}</span>
            {live && experience.profile.experiment_eligible && (
              <span>
                {experience.decision.evaluation_reason?.inExperiment === true
                  ? "In experiment"
                  : "Not enrolled in an experiment for this evaluation"}
              </span>
            )}
          </div>
        )}
        {live && (
          <div className="context-box">
            <code>{experience.integration.flag_key}</code>
            <span>Source: {experience.decision.source}</span>
            <span>Stream: {experience.integration.state}</span>
            <span>SDK fallback: {String(experience.decision.fallback)}</span>
          </div>
        )}
        {state && (
          <>
            {!live && (
              <>
                <label htmlFor="release">Experience preview</label>
                <select
                  id="release"
                  disabled={busy}
                  value={state.release}
                  onChange={(event) =>
                    update({ ...state, release: event.target.value })
                  }
                >
                  <option value="existing">Existing for everyone</option>
                  <option value="targeted">QA + premium preview</option>
                  <option value="new">New for everyone</option>
                </select>
              </>
            )}
            <label className="checkbox">
              <input
                type="checkbox"
                checked={state.incident}
                disabled={busy}
                onChange={(event) =>
                  update({ ...state, incident: event.target.checked })
                }
              />{" "}
              Simulate new-panel failure
            </label>
            <button
              className="secondary full"
              disabled={busy}
              onClick={() => update({ release: "targeted", incident: false })}
            >
              <RotateCcw size={16} />{" "}
              {live ? "Reset incident simulation" : "Reset preview"}
            </button>
          </>
        )}
        {error && (
          <p role="alert" className="error-text">
            {error}
          </p>
        )}
        <h3>Integration checklist</h3>
        <p className="small">
          SDK status is shown below. Verify event ingestion, recordings, and
          experiment results in LaunchDarkly.
        </p>
        <ul className="checklist">
          {capabilities.map(([capability, status]) => (
            <li key={capability}>
              <span>{capability}</span>
              <small>{status}</small>
            </li>
          ))}
        </ul>
        <h3>Local activity</h3>
        <p className="small">
          In-memory app activity only. Not LaunchDarkly telemetry or experiment
          results.
        </p>
        {activity.length === 0 ? (
          <p className="small">
            Explore an offer or change a preview setting to begin.
          </p>
        ) : (
          <ul className="activity">
            {activity.slice(0, 8).map((entry, index) => (
              <li key={index}>
                <code>{entry.name}</code>
                <span>{Object.values(entry.attributes).join(" · ")}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
// DEMO END presenter-controls
