using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Dtos.Timetable
{
    public class UpsertWorkoutRequest
    {
        [Required]
        [MaxLength(100)]
        public string Name { get; set; } = string.Empty;

        [Required]
        [MaxLength(100)]
        public string Category { get; set; } = string.Empty;

        [MaxLength(500)]
        public string? Description { get; set; }
    }
}
