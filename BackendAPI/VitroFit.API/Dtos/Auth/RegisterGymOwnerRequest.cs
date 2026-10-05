namespace VitroFit.API.Dtos.Auth
{
    /// <summary>Multipart form posted by the "Register your gym" wizard.</summary>
    public sealed class RegisterGymOwnerRequest
    {
        public string FirstName { get; set; } = string.Empty;
        public string LastName { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
        public string Phone { get; set; } = string.Empty;
        public string Password { get; set; } = string.Empty;

        public string GymName { get; set; } = string.Empty;
        public string OwnerRole { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Address { get; set; } = string.Empty;
        public string City { get; set; } = string.Empty;
        public string GymPhone { get; set; } = string.Empty;
        public string ContactEmail { get; set; } = string.Empty;
        public string Website { get; set; } = string.Empty;
        public string? OpeningHours { get; set; }

        public List<string> Equipment { get; set; } = new();
        public List<string> Classes { get; set; } = new();

        public List<IFormFile> GymPhotos { get; set; } = new();
        public List<IFormFile> EquipmentPhotos { get; set; } = new();
        public IFormFile? License { get; set; }
    }

    /// <summary>Outcome of a gym owner registration or re-application.</summary>
    public sealed record RegisterGymOwnerResult(string Message, string Email, bool EmailVerificationRequired);

    /// <summary>
    /// Outcome of verifying an email. Normal accounts get tokens straight away; gym owners whose
    /// application is not yet approved get a status instead.
    /// </summary>
    public sealed record VerifyEmailResult(AuthResponse? Auth, string? PendingStatus, string? Message);
}
