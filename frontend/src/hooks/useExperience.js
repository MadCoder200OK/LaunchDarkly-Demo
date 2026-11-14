// Subscribe to Python's event stream; Python owns flag evaluation for the selected profile.
import { useEffect, useState } from 'react';

// DEMO START browser-stream: Subscribe to evaluated server updates and refresh the displayed experience without reload.
export function useExperience(profileKey) {
  const [experience, setExperience] = useState(null);
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    // Replace the subscription when the visitor changes so old profile values cannot leak across views.
    setExperience(null);
    setConnected(false);
    const stream = new EventSource(`/api/stream?profile_key=${encodeURIComponent(profileKey)}`);
    stream.onmessage = (event) => { setExperience(JSON.parse(event.data)); setConnected(true); };
    // EventSource reconnects automatically; retain the last view while showing transport status.
    stream.onerror = () => setConnected(false);
    return () => stream.close();
  }, [profileKey]);
  return { experience, connected };
}
// DEMO END browser-stream
