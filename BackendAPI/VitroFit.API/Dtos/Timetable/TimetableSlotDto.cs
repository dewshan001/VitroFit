namespace VitroFit.API.Dtos.Timetable
{
    public class TimetableSlotDto
    {
        public int Id { get; set; }
        public DayOfWeek Day { get; set; }
        public TimeSpan StartTime { get; set; }
        public TimeSpan EndTime { get; set; }
        public string Title { get; set; } = string.Empty;
        public int WorkoutId { get; set; }
        public string WorkoutName { get; set; } = string.Empty;
        public string WorkoutCategory { get; set; } = string.Empty;
    }
}
