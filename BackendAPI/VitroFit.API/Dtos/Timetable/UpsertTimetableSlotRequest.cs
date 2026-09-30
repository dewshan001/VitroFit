using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Dtos.Timetable
{
    public class UpsertTimetableSlotRequest
    {
        [Required]
        public DayOfWeek Day { get; set; }

        [Required]
        public TimeSpan StartTime { get; set; }

        [Required]
        public TimeSpan EndTime { get; set; }

        [Required]
        [MaxLength(100)]
        public string Title { get; set; } = string.Empty;

        [Required]
        public int WorkoutId { get; set; }
    }
}
