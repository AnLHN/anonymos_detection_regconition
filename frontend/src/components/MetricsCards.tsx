export default function MetricsCards({ alerts, cameras, rules, employees }: { alerts: number; cameras: number; rules: number; employees: number }) {
  return (
    <section className="grid metrics">
      <Metric label="Alerts" value={alerts} />
      <Metric label="Cameras" value={cameras} />
      <Metric label="Rules" value={rules} />
      <Metric label="Employees" value={employees} />
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <article className="card metric-card">
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
