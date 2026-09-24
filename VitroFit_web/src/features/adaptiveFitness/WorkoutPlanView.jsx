const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function WorkoutPlanView({ plans = [], catalog = [] }) {
  if (!plans.length) return null;

  const plansByWeek = new Map(plans.map(item => [item.plan.week, item.plan]));
  return <section className="fitness-week-grid">
    <h3>Weekly schedule</h3>
    <p>Each new week is generated after you record progress for the current schedule.</p>
    <div className="fitness-week-scroll">
      <table className="fitness-week-table">
        <thead><tr><th scope="col">Day</th>{[1, 2, 3, 4].map(week => <th scope="col" key={week}>Week {week}</th>)}</tr></thead>
        <tbody>{weekdays.map((weekday, index) => {
          const day = index + 1;
          return <tr key={day}><th scope="row">{weekday}</th>{[1, 2, 3, 4].map(week => {
            const plan = plansByWeek.get(week);
            const session = plan?.days.find(item => item.day === day);
            return <td key={week}>
              {!plan ? <span className="fitness-week-pending">Generated after progress</span> : !session ? <span>Rest / recovery</span> : <>
                <strong>{session.focus}</strong>
                <small>Warm up {session.warmupMinutes} min · Cool down {session.cooldownMinutes} min</small>
                <ul>{session.exercises.map(item => {
                  const exercise = catalog.find(value => value.id === item.exerciseId);
                  return <li key={item.exerciseId}>
                    <strong>{exercise?.name || `Exercise ${item.exerciseId}`}</strong><br />
                    {item.sets} sets × {item.repetitions} reps · rest {item.restSeconds}s
                  </li>;
                })}</ul>
              </>}
            </td>;
          })}</tr>;
        })}</tbody>
      </table>
    </div>
  </section>;
}
