export default function FitnessCycleView({ cycle }) {
  if (!cycle) return null;
  const analysis = cycle.analysis ?? cycle.Analysis ?? {};
  const value = (camel, pascal, fallback = 0) => analysis[camel] ?? analysis[pascal] ?? fallback;
  const startDate = cycle.startDate ?? cycle.StartDate ?? '—';
  const endDate = cycle.endDate ?? cycle.EndDate ?? '—';
  const weeks = value('weeks', 'Weeks', []);
  return <section className="fitness-cycle-result" aria-labelledby="fitness-cycle-title">
    <span className="fitness-eyebrow">Three-month analysis period</span>
    <h2 id="fitness-cycle-title">Your progressive training cycle</h2>
    <p>{startDate} to {endDate}. Workouts are generated in 3 or 4 day blocks as you record progress.</p>
    <div className="fitness-cycle-analysis">
      <span><strong>{value('completedSessions', 'CompletedSessions')}</strong> workouts completed</span>
      <span><strong>{value('plannedSessions', 'PlannedSessions')}</strong> planned across analyzed blocks</span>
      <span><strong>{value('skippedSessions', 'SkippedSessions')}</strong> incomplete sessions</span>
      <span><strong>{value('painReports', 'PainReports')}</strong> pain reports recorded</span>
      <span><strong>{value('averageRpe', 'AverageRpe', null) == null ? '—' : Number(value('averageRpe', 'AverageRpe')).toFixed(1)}</strong> average effort / 10</span>
    </div>
    {Array.isArray(weeks) && weeks.length > 0 && <details className="fitness-cycle-disclosure">
      <summary>View training history analysis</summary>
      <ol className="fitness-cycle-days">{weeks.map(block => <li key={block.week ?? block.Week}>
        <strong>Block {Math.max(1, (block.week ?? block.Week) - 4)}</strong>
        <span>{block.completedSessions ?? block.CompletedSessions ?? 0} workouts · {block.painReports ?? block.PainReports ?? 0} pain reports · {block.totalVolume ?? block.TotalVolume ?? 0} volume</span>
      </li>)}</ol>
    </details>}
    <p className="fitness-guidance-copy">Every scheduled entry is a workout. Rest days and recovery-only days are not generated. Choose separate rest time between sessions as needed.</p>
  </section>;
}
