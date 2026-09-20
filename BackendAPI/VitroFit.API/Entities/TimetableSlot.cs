using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Entities
{
    public class TimetableSlot
    {
        public int Id { get; set; }

        public int UserId { get; set; }

        public User? User { get; set; }

        public int WorkoutId { get; set; }

        public Workout? Workout { get; set; }

        public DayOfWeek Day { get; set; }

        public TimeSpan StartTime { get; set; }

        public TimeSpan EndTime { get; set; }

        [Required]
        [MaxLength(100)]
        public string Title { get; set; } = string.Empty;

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    }
}
