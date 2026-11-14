// Navigate fictional identities only; Python and LaunchDarkly still own variation assignment.
// DEMO START experiment-visitors: Select stable eligible visitors without assigning their experiment treatment locally.
export default function ExperimentVisitors({ profiles, selected, onSelect }) {
  const visitors = profiles.filter((profile) => profile.experiment_eligible);
  const index = visitors.findIndex((profile) => profile.key === selected);
  if (index < 0) return null;

  return <section className="experiment-visitors" aria-label="Experiment visitors">
    <strong>Demo visitor {index + 1} of {visitors.length}</strong>
    <div className="visitor-actions">
      <button className="secondary" disabled={index === 0} onClick={() => onSelect(visitors[index - 1].key)}>Previous visitor</button>
      <button className="secondary" disabled={index === visitors.length - 1} onClick={() => onSelect(visitors[index + 1].key)}>Next visitor</button>
    </div>
    <p className="small">Each fictional visitor has a stable identity. Explore offers as different visitors, then revisit one to check its assignment. This small demo cohort cannot establish a winner.</p>
  </section>;
}
// DEMO END experiment-visitors
