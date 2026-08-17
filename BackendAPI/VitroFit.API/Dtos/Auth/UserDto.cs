using VitroFit.API.Entities;

namespace VitroFit.API.Dtos.Auth
{
    public sealed class UserDto
    {
        public int Id { get; set; }
        public string FirstName { get; set; } = string.Empty;
        public string LastName { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
        public string? Phone { get; set; }
        public string? ProfileImageUrl { get; set; }
        public UserRole Role { get; set; }
    }
}
