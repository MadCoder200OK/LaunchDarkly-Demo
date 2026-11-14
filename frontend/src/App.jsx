// Page composition. Provider behavior stays behind the experience hook and Python API.
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  ShieldCheck,
  SlidersHorizontal,
  X,
  CheckCircle2,
} from "lucide-react";
import { api } from "./services/api";
import { useExperience } from "./hooks/useExperience";
import Offers from "./components/Offers";
import OffersHero from "./components/OffersHero";
import Assistant from "./components/Assistant";
import DemoPanel from "./components/DemoPanel";
import { useTelemetry } from "./hooks/useTelemetry";
import { telemetry } from "./services/telemetry";

// DEMO START app-shell: Connect the customer journey, visitor selection, engagement, and accessible outcome dialogs.
export default function App() {
  const [profiles, setProfiles] = useState([]);
  const [selected, setSelected] = useState("premium-001");
  const [studio, setStudio] = useState(false);
  const [notice, setNotice] = useState(null);
  const [bootError, setBootError] = useState("");
  const dialog = useRef(null);
  const { experience, connected } = useExperience(selected);
  const diagnostics = useTelemetry(experience?.profile);
  const profile = profiles.find((visitor) => visitor.key === selected) ?? experience?.profile;
  const live = experience?.mode === "launchdarkly";
  const sdkConnected = experience?.integration?.connected;
  useEffect(() => {
    api
      .profiles()
      .then(setProfiles)
      .catch(() =>
        setBootError(
          "The Python API is unavailable. Start the backend and reload to try again.",
        ),
      );
  }, []);
  useEffect(() => {
    if (notice && dialog.current && !dialog.current.open)
      dialog.current.showModal();
  }, [notice]);
  async function explore(offer) {
    // Confirm the action through Python, which also enforces the simulated incident response.
    setNotice({
      title: offer.title.replace("\n", " "),
      message: "Opening your offer…",
    });
    try {
      const result = await telemetry.offer(experience, offer.id, () =>
        api.engage(selected, offer.id),
      );
      setNotice({
        title: "A little more possibility.",
        message: result.message,
      });
    } catch (failure) {
      setNotice({
        title: "We hit a little bump.",
        message: failure.message,
        error: true,
        simulatedIncident: failure.code === "simulated_offer_incident",
      });
    }
  }
  return (
    <>
      <div className="preview-bar">
        <span>
          <span className="status-dot" />{" "}
          {live ? "LAUNCHDARKLY DEMO" : "APPLICATION PREVIEW"}{" "}
          <span className="bar-separator">/</span> Fictional banking. Real
          possibilities.
        </span>
        <button onClick={() => setStudio(true)}>
          Demo studio <SlidersHorizontal size={13} />
        </button>
      </div>
      <header className="site-header">
        <a className="brand" href="#">
          <span className="brand-symbol">a</span> abc<span>bank</span>
          <span className="brand-period">.</span>
        </a>
        <nav aria-label="Main navigation">
          <a href="#offers">Your possibilities</a>
          <a href="#why">The ABC way</a>
          <button
            className="nav-assistant"
            onClick={() => document.querySelector(".chat-launch").click()}
          >
            Here to help <ArrowUpRight size={14} />
          </button>
        </nav>
        <div className="profile-badge">
          <span className="avatar">
            {profile?.name
              .split(" ")
              .map((word) => word[0])
              .join("") || "—"}
          </span>
          <div>
            <strong>{profile?.name || "Loading visitor"}</strong>
            <small>{profile?.role || "Demo visitor"}</small>
          </div>
        </div>
      </header>
      <main>
        <OffersHero experience={experience} />
        <div className="trust-strip">
          <span>More than a bank. A partner in your plans.</span>
          <span>
            <ShieldCheck size={15} /> Simple by design
          </span>
          <span>✧ &nbsp; Possibilities for everyone</span>
          <span>↗ &nbsp; Room to grow</span>
        </div>
        {bootError ? (
          <div className="page-message error-text" role="alert">
            {bootError}
          </div>
        ) : experience ? (
          <Offers experience={experience} onExplore={explore} />
        ) : (
          <div className="page-message" role="status">
            {connected
              ? "Finding your possibilities…"
              : "Connecting to your local demo…"}
          </div>
        )}
        <section className="why-section" id="why">
          <div className="why-mark">✳</div>
          <div>
            <p className="eyebrow">THE ABC WAY</p>
            <h2>
              Your life doesn't stand still.
              <br />
              Neither should your bank.
            </h2>
          </div>
          <p>
            Small moments. Big milestones. We believe banking should meet you
            wherever you are, with more ways to move forward.
          </p>
        </section>
      </main>
      <footer>
        <a className="brand footer-brand" href="#">
          abc bank.
        </a>
        <p>A fictional experience, built for a LaunchDarkly demo.</p>
        <span
          className={`connection ${connected && (!live || sdkConnected) ? "online" : ""}`}
        >
          <span className="status-dot" />
          {!connected
            ? "Reconnecting to application"
            : live
              ? sdkConnected
                ? "LaunchDarkly stream connected"
                : "LaunchDarkly reconnecting · cached values or safe fallback"
              : "Local preview connected"}
        </span>
      </footer>
      <Assistant
        key={selected}
        profileKey={selected}
        aiStatus={diagnostics.config?.ai}
      />
      {studio && (
        <DemoPanel
          profiles={profiles}
          selected={selected}
          onSelect={setSelected}
          experience={experience}
          diagnostics={diagnostics}
          onClose={() => setStudio(false)}
        />
      )}
      <dialog
        ref={dialog}
        aria-labelledby="offer-dialog-title"
        onCancel={() => setNotice(null)}
        onClose={() => setNotice(null)}
        className="offer-dialog"
      >
        {notice && (
          <>
            <button
              className="icon-button dialog-close"
              aria-label="Close offer details"
              onClick={() => dialog.current.close()}
            >
              <X size={21} />
            </button>
            <CheckCircle2
              size={35}
              className={notice.error ? "error-text" : "success-icon"}
            />
            <p className="eyebrow">
              {notice.error
                ? notice.simulatedIncident
                  ? "SIMULATED INCIDENT"
                  : "SERVICE UNAVAILABLE"
                : "DEMO OFFER"}
            </p>
            <h2 id="offer-dialog-title">{notice.title}</h2>
            <p>{notice.message}</p>
            <button className="primary" onClick={() => dialog.current.close()}>
              Back to possibilities <ArrowRight size={16} />
            </button>
          </>
        )}
      </dialog>
    </>
  );
}
// DEMO END app-shell
