/**
 * JarvisOrb — Animated arc-reactor-style indicator.
 * Purely visual; driven by the existing `active` (busy) prop.
 */
export function JarvisOrb({ active }: { active: boolean }) {
  return (
    <div className={`jarvis-orb${active ? " active" : ""}`}>
      <div className="orb-ring" />
      <div className="orb-ring orb-ring-2" />
      <div className="orb-core" />
    </div>
  );
}
