using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Entities
{
    /// <summary>Shared catalog of workouts users can schedule into their timetable.</summary>
    public class Workout
    {
        public int Id { get; set; }

        [Required]
        [MaxLength(100)]
        public string Name { get; set; } = string.Empty;

        [Required]
        [MaxLength(100)]
        public string Category { get; set; } = string.Empty;

        [MaxLength(500)]
        public string? Description { get; set; }

        public ICollection<TimetableSlot> TimetableSlots { get; set; } = new List<TimetableSlot>();
    }
}
