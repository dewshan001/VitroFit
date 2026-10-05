const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const weeks = [1, 2, 3, 4];

export default function WorkoutPlanView({ plans = [], catalog = [], progressByWeek = {}, timetable = null, longTermImpact = "" }) {
  if (!plans.length) return null;

  const sortedPlans = [...plans].sort((a, b) => (a.plan?.week || 0) - (b.plan?.week || 0));
  const plansByWeek = new Map(sortedPlans.map(item => [item.plan.week, item.plan]));
  const latestPlan = sortedPlans.at(-1)?.plan;

  const renderTimetable = () => {
    if (!timetable) return null;
    return (
      <section className="fitness-timetable-section" aria-labelledby="fitness-timetable-title">
        <div className="fitness-week-heading">
          <div>
            <span className="fitness-eyebrow">Smart Scheduling</span>
            <h3 id="fitness-timetable-title">Your Automated Timetable</h3>
          </div>
        </div>
        
        {longTermImpact && (
          <div className="fitness-long-term-impact fitness-progression-note">
            <span className="fitness-eyebrow">Long-term Impact</span>
            <p>{longTermImpact}</p>
          </div>
        )}
        
        <div className="fitness-timetable-grid">
          {timetable.slots?.map((slot, idx) => {
            const session = latestPlan?.days.find(item => item.day === slot.day);
            return (
              <div key={idx} className="fitness-timetable-card">
                <span className="fitness-eyebrow">{weekdays[slot.day - 1]}</span>
                <h4>{slot.focus}</h4>
                <p><strong>Time:</strong> {slot.startTime} &mdash; {slot.endTime} ({slot.durationMinutes} min)</p>
                
                {session && (
                  <>
                    <p style={{ marginTop: '0.5rem', marginBottom: '1rem', color: '#ccc' }}>Warm up {session.warmupMinutes} min · Cool down {session.cooldownMinutes} min</p>
                    <ul className="fitness-exercise-list">{session.exercises.map(item => {
                      const exercise = catalog.find(value => value.id === item.exerciseId);
                      return <li key={item.exerciseId}>
                        <strong className="fitness-exercise-name">{exercise?.name || `Exercise ${item.exerciseId}`}</strong>
                        <span className="fitness-exercise-prescription">{item.sets} sets × {item.repetitions} reps</span>
                        <small className="fitness-exercise-rest">Rest {item.restSeconds} sec</small>
                        {item.adaptedFromExerciseId && <small className="fitness-adaptation-reason">Adapted from exercise {item.adaptedFromExerciseId}: {item.adaptationReason || 'changed to account for your pain report'}</small>}
                      </li>;
                    })}</ul>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </section>
    );
  };


  if (latestPlan?.week > 4) return <section className="fitness-week-grid fitness-block-plan" aria-labelledby="fitness-week-title">
    <div className="fitness-week-heading">
      <div><span className="fitness-eyebrow">Progressive workout block</span><h3 id="fitness-week-title">Block {latestPlan.week - 4}</h3></div>
      <p>Complete and record every workout to unlock the next 3 or 4 day block.</p>
    </div>
    <ol className="fitness-block-days">{latestPlan.days.map((session, index) => <li key={session.day}>
      <header><span>Day {String(index + 1).padStart(2, '0')}</span></header>
      <h4>{session.focus}</h4>
      <p>Warm up {session.warmupMinutes} min · Cool down {session.cooldownMinutes} min</p>
      <ul className="fitness-exercise-list">{session.exercises.map(item => {
        const exercise = catalog.find(value => value.id === item.exerciseId);
        return <li key={item.exerciseId}>
          <strong className="fitness-exercise-name">{exercise?.name || `Exercise ${item.exerciseId}`}</strong>
          <span className="fitness-exercise-prescription">{item.sets} sets × {item.repetitions} reps</span>
          <small className="fitness-exercise-rest">Rest {item.restSeconds} sec</small>
          {item.adaptedFromExerciseId && <small className="fitness-adaptation-reason">Adapted from exercise {item.adaptedFromExerciseId}: {item.adaptationReason || 'changed to account for your pain report'}</small>}
        </li>;
      })}</ul>
    </li>)}</ol>
    {renderTimetable()}
  </section>;

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

    {renderTimetable()}
  </section>;
}
