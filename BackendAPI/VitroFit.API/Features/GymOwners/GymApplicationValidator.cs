using System.Net.Mail;
using System.Text.RegularExpressions;

namespace VitroFit.API.Features.GymOwners
{
    /// <summary>Metadata of one uploaded file, with its first bytes so the real type can be checked.</summary>
    public sealed record UploadedFileInfo(string FileName, string ContentType, long Length, byte[] Header);

    /// <summary>The values a gym owner submits when registering. Kept free of ASP.NET types so it is easy to test.</summary>
    public sealed class GymApplicationInput
    {
        public string FirstName { get; init; } = "";
        public string LastName { get; init; } = "";
        public string Email { get; init; } = "";
        public string Phone { get; init; } = "";
        public string Password { get; init; } = "";
        public string GymName { get; init; } = "";
        public string OwnerRole { get; init; } = "";
        public string Description { get; init; } = "";
        public string Address { get; init; } = "";
        public string City { get; init; } = "";
        public string GymPhone { get; init; } = "";
        public string ContactEmail { get; init; } = "";
        public string Website { get; init; } = "";
        public string? OpeningHours { get; init; }
        public IReadOnlyList<string> Equipment { get; init; } = Array.Empty<string>();
        public IReadOnlyList<string> Classes { get; init; } = Array.Empty<string>();
        public IReadOnlyList<UploadedFileInfo> GymPhotos { get; init; } = Array.Empty<UploadedFileInfo>();
        public IReadOnlyList<UploadedFileInfo> EquipmentPhotos { get; init; } = Array.Empty<UploadedFileInfo>();
        public UploadedFileInfo? License { get; init; }
    }

    /// <summary>Thrown with every problem found, so the form can show them all at once.</summary>
    public sealed class GymApplicationValidationException : InvalidOperationException
    {
        public IReadOnlyList<string> Errors { get; }

        public GymApplicationValidationException(IReadOnlyList<string> errors)
            : base(errors.Count > 0 ? errors[0] : "The application is not valid.")
        {
            Errors = errors;
        }
    }

    public static class GymApplicationValidator
    {
        public const long MaxImageBytes = 5 * 1024 * 1024;
        public const long MaxLicenseBytes = 5 * 1024 * 1024;
        public const int MinPhotos = 1;
        public const int MaxPhotos = 5;
        public const int MaxEquipment = 30;
        public const int MaxClasses = 20;
        public const int MaxTagLength = 60;
        public const int MinPasswordLength = 8;
        public static readonly string[] OwnerRoles = { "Owner", "Manager" };

        private static readonly Regex PhonePattern = new(@"^\+?[0-9 ()\-]{7,20}$", RegexOptions.Compiled);

        public enum FileKind { Unknown, Jpeg, Png, WebP, Pdf }

        /// <summary>Checks the gym details only (also used when a rejected owner re-applies).</summary>
        public static List<string> ValidateGymDetails(GymApplicationInput input)
        {
            var errors = new List<string>();

            Required(errors, input.GymName, "Gym name", 150);

            if (string.IsNullOrWhiteSpace(input.OwnerRole))
                errors.Add("Your role is required.");
            else if (!OwnerRoles.Contains(input.OwnerRole.Trim(), StringComparer.OrdinalIgnoreCase))
                errors.Add("Your role must be Owner or Manager.");

            Required(errors, input.Address, "Address", 300);
            Required(errors, input.City, "City", 100);

            if (string.IsNullOrWhiteSpace(input.GymPhone) || !PhonePattern.IsMatch(input.GymPhone.Trim()))
                errors.Add("Enter a valid gym phone number.");

            if (!IsEmail(input.ContactEmail))
                errors.Add("Enter a valid public contact email for the gym.");

            if (!IsHttpsUrl(input.Website))
                errors.Add("Enter the gym website as a full https:// address.");

            if (string.IsNullOrWhiteSpace(input.Description) || input.Description.Trim().Length < 30)
                errors.Add("Describe your gym in at least 30 characters.");
            else if (input.Description.Trim().Length > 1500)
                errors.Add("The description must be 1500 characters or fewer.");

            if (!string.IsNullOrWhiteSpace(input.OpeningHours) && input.OpeningHours.Trim().Length > 300)
                errors.Add("Opening hours must be 300 characters or fewer.");

            ValidateTags(errors, input.Equipment, "equipment item", MaxEquipment, required: true);
            ValidateTags(errors, input.Classes, "class", MaxClasses, required: false);

            ValidatePhotos(errors, input.GymPhotos, "gym");
            ValidatePhotos(errors, input.EquipmentPhotos, "equipment");

            if (input.License != null)
            {
                var kind = DetectKind(input.License.Header);
                if (input.License.Length == 0)
                    errors.Add("The licence document is empty.");
                else if (kind is not (FileKind.Pdf or FileKind.Jpeg or FileKind.Png))
                    errors.Add("The licence document must be a PDF, JPG or PNG file.");
                else if (input.License.Length > MaxLicenseBytes)
                    errors.Add("The licence document must be 5 MB or smaller.");
            }

            return errors;
        }

        /// <summary>Checks the account fields and the gym details.</summary>
        public static List<string> Validate(GymApplicationInput input)
        {
            var errors = new List<string>();

            Required(errors, input.FirstName, "First name", 100);
            Required(errors, input.LastName, "Last name", 100);

            if (!IsEmail(input.Email))
                errors.Add("Enter a valid email address.");
            if (string.IsNullOrWhiteSpace(input.Phone) || !PhonePattern.IsMatch(input.Phone.Trim()))
                errors.Add("Enter a valid phone number.");
            if (string.IsNullOrEmpty(input.Password) || input.Password.Length < MinPasswordLength)
                errors.Add($"The password must be at least {MinPasswordLength} characters.");

            errors.AddRange(ValidateGymDetails(input));
            return errors;
        }

        /// <summary>Identifies a file by its first bytes, ignoring the client-supplied content type.</summary>
        public static FileKind DetectKind(byte[] header)
        {
            if (header.Length >= 3 && header[0] == 0xFF && header[1] == 0xD8 && header[2] == 0xFF)
                return FileKind.Jpeg;
            if (header.Length >= 8 && header[0] == 0x89 && header[1] == 0x50 && header[2] == 0x4E && header[3] == 0x47
                && header[4] == 0x0D && header[5] == 0x0A && header[6] == 0x1A && header[7] == 0x0A)
                return FileKind.Png;
            if (header.Length >= 12 && header[0] == 'R' && header[1] == 'I' && header[2] == 'F' && header[3] == 'F'
                && header[8] == 'W' && header[9] == 'E' && header[10] == 'B' && header[11] == 'P')
                return FileKind.WebP;
            if (header.Length >= 5 && header[0] == '%' && header[1] == 'P' && header[2] == 'D' && header[3] == 'F' && header[4] == '-')
                return FileKind.Pdf;
            return FileKind.Unknown;
        }

        public static string[] CleanTags(IEnumerable<string>? tags) =>
            (tags ?? Array.Empty<string>())
                .Select(t => t?.Trim() ?? "")
                .Where(t => t.Length > 0)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToArray();

        public static bool IsEmail(string? value)
        {
            if (string.IsNullOrWhiteSpace(value) || value.Length > 200) return false;
            try
            {
                var trimmed = value.Trim();
                var address = new MailAddress(trimmed);
                return address.Address == trimmed && address.Host.Contains('.');
            }
            catch (FormatException)
            {
                return false;
            }
        }

        public static bool IsHttpsUrl(string? value)
        {
            if (string.IsNullOrWhiteSpace(value) || value.Length > 300) return false;
            return Uri.TryCreate(value.Trim(), UriKind.Absolute, out var uri)
                   && uri.Scheme == Uri.UriSchemeHttps
                   && uri.Host.Contains('.')
                   && string.IsNullOrEmpty(uri.UserInfo);
        }

        private static void ValidatePhotos(List<string> errors, IReadOnlyList<UploadedFileInfo> photos, string label)
        {
            if (photos.Count < MinPhotos)
            {
                errors.Add($"Upload at least {MinPhotos} {label} photo.");
                return;
            }
            if (photos.Count > MaxPhotos)
            {
                errors.Add($"Upload at most {MaxPhotos} {label} photos.");
                return;
            }
            foreach (var photo in photos)
            {
                var kind = DetectKind(photo.Header);
                if (kind is not (FileKind.Jpeg or FileKind.Png or FileKind.WebP))
                    errors.Add($"\"{photo.FileName}\" is not a JPG, PNG or WebP image.");
                else if (photo.Length > MaxImageBytes)
                    errors.Add($"\"{photo.FileName}\" is larger than 5 MB.");
            }
        }

        private static void ValidateTags(List<string> errors, IReadOnlyList<string> raw, string label, int max, bool required)
        {
            var tags = CleanTags(raw);
            if (required && tags.Length == 0)
                errors.Add($"Add at least one {label}.");
            if (tags.Length > max)
                errors.Add($"Add at most {max} {label}s.");
            if (tags.Any(t => t.Length > MaxTagLength))
                errors.Add($"Each {label} must be {MaxTagLength} characters or fewer.");
        }

        private static void Required(List<string> errors, string? value, string label, int max)
        {
            if (string.IsNullOrWhiteSpace(value))
                errors.Add($"{label} is required.");
            else if (value.Trim().Length > max)
                errors.Add($"{label} must be {max} characters or fewer.");
        }
    }
}
