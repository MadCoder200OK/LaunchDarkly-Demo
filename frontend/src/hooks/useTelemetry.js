// Keep telemetry initialization outside presentation components and flag-rendering decisions.
import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { telemetry } from '../services/telemetry';

// DEMO START browser-identity: Initialize public browser instrumentation and follow the selected fictional visitor.
export function useTelemetry(profile) {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState('loading');
  useEffect(() => {
    let active = true;
    api.config().then((value) => { if (active) setConfig(value); })
      .catch(() => { if (active) setStatus('unavailable'); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!config || !profile) return;
    let active = true;
    setStatus('initializing');
    telemetry.identify(config, profile).then((value) => { if (active) setStatus(value); })
      .catch(() => { if (active) setStatus('unavailable'); });
    return () => { active = false; };
  }, [config, profile?.key]);
  return { config, status };
}
// DEMO END browser-identity
