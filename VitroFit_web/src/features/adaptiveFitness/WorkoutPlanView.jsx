const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const weeks = [1, 2, 3, 4];

export default function WorkoutPlanView({ plans = [], catalog = [], progressByWeek = {} }) {
  if (!plans.length) return null;

  const plansByWeek = new Map(plans.map(item => [item.plan.week, item.plan]));

  return <section className="fitness-week-grid" aria-labelledby="fitness-week-title">
    <div className="fitness-week-heading">
      <div>
        <span className="fitness-eyebrow">Your training calendar</span>
        <h3 id="fitness-week-title">Weekly schedule</h3>
      </div>
      <p>Record your sessions to unlock the next week of your beginner plan.</p>
    </div>
    <aside className="fitness-week-safety-note" role="note">
      <span className="fitness-week-safety-icon" aria-hidden="true">!</span>
      <p><strong>Progress gradually and listen to your body.</strong> Increase workout weight only in small steps as you move through the weeks. Stop if you feel pain. If pain is severe or continues, contact a gym instructor or qualified health professional before exercising again.</p>
    </aside>

    <div className="fitness-week-scroll" role="region" aria-label="Four-week training schedule" tabIndex="0">
      <table className="fitness-week-table">
        <thead>
          <tr>
            <th scope="col">Training day</th>
            {weeks.map(week => <th scope="col" key={week}>Week <span>{week}</span></th>)}
          </tr>
        </thead>
        <tbody>
          {weekdays.map((weekday, index) => {
            const day = index + 1;

            return <tr key={day}>
              <th scope="row">{weekday}</th>
              {weeks.map(week => {
                const plan = plansByWeek.get(week);
                const session = plan?.days.find(item => item.day === day);

                if (!plan) {
                  return <td className="fitness-week-pending-cell" key={week}>
                    <span className="fitness-week-pending"><i aria-hidden="true">↗</i>Available after progress</span>
                  </td>;
                }

                if (!session) {
                  return <td className="fitness-week-rest-cell" key={week}>
                    <span className="fitness-week-rest">
                      <i aria-hidden="true">—</i>
                      <strong>Rest &amp; recovery</strong>
                      <small>Give your body time to recover.</small>
                    </span>
                  </td>;
                }

                return <td key={week}>
                  <span className="fitness-focus-label">{session.focus}</span>
                  {(() => {
                    const saved = progressByWeek[week]?.find(record => record.day === day);
                    return <span className={`fitness-week-progress${saved?.completed ? ' is-complete' : saved ? ' is-incomplete' : ''}`}>
                      {saved ? `${saved.completed ? 'Completed' : 'Recorded'} · ${saved.performedOn}` : 'Not completed'}
                    </span>;
                  })()}
                  <span className="fitness-session-meta">Warm up {session.warmupMinutes} min <i>·</i> Cool down {session.cooldownMinutes} min</span>
                  <ul className="fitness-exercise-list">
                    {session.exercises.map(item => {
                      const exercise = catalog.find(value => value.id === item.exerciseId);

                      return <li key={item.exerciseId}>
                        <strong className="fitness-exercise-name">{exercise?.name || `Exercise ${item.exerciseId}`}</strong>
                        <span className="fitness-exercise-prescription">{item.sets} sets <i>×</i> {item.repetitions} reps</span>
                        <small className="fitness-exercise-rest">Rest {item.restSeconds} sec</small>
                      </li>;
                    })}
                  </ul>
                </td>;
              })}
            </tr>;
          })}
        </tbody>
      </table>
    </div>
  </section>;
}
