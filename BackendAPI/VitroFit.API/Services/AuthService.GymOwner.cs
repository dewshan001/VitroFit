using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Dtos.Auth;
using VitroFit.API.Entities;
using VitroFit.API.Features.GymOwners;

namespace VitroFit.API.Services
{
    // Gym owner registration and the approval gate. Split out of AuthService.cs to keep that file readable.
    public sealed partial class AuthService
    {
        public async Task<RegisterGymOwnerResult> RegisterGymOwnerAsync(RegisterGymOwnerRequest request)
        {
            var input = await ToInputAsync(request);
            var email = input.Email.Trim();

            var existing = await _dbContext.Users.SingleOrDefaultAsync(u => u.Email == email);
            if (existing != null)
            {
                return await ReapplyAsync(existing, input, request);
            }

            var errors = GymApplicationValidator.Validate(input);
            if (errors.Count > 0) throw new GymApplicationValidationException(errors);

            var uploaded = new List<string>();
            try
            {
                var application = await UploadApplicationAsync(input, request, uploaded);

                var user = new User
                {
                    FirstName       = input.FirstName.Trim(),
                    LastName        = input.LastName.Trim(),
                    Email           = email,
                    Phone           = input.Phone.Trim(),
                    Role            = UserRole.Gym_Owner,
                    IsEmailVerified = false
                };
                user.PasswordHash = _passwordHasher.HashPassword(user, input.Password);

                application.User = user;
                _dbContext.Users.Add(user);
                _dbContext.GymApplications.Add(application);
                await _dbContext.SaveChangesAsync();

                await SendOtpAsync(user, OtpPurpose.EmailVerification);

                return new RegisterGymOwnerResult(
                    "Application received. Please check your email for a 6-digit code to verify your address.",
                    user.Email,
                    EmailVerificationRequired: true);
            }
            catch
            {
                // If the account was never saved, do not leave the uploaded files behind.
                if (!await _dbContext.Users.AnyAsync(u => u.Email == email))
                {
                    await DeleteUrlsAsync(uploaded);
                }
                throw;
            }
        }

        /// <summary>A rejected owner proves who they are with email + password and replaces the application.</summary>
        private async Task<RegisterGymOwnerResult> ReapplyAsync(User user, GymApplicationInput input, RegisterGymOwnerRequest request)
        {
            var application = await GetGymApplicationAsync(user);
            var passwordOk = user.Role == UserRole.Gym_Owner
                && _passwordHasher.VerifyHashedPassword(user, user.PasswordHash, input.Password) != PasswordVerificationResult.Failed;

            // Same message as a plain duplicate, so this cannot be used to probe which emails are owners.
            if (application == null || !passwordOk)
            {
                throw new InvalidOperationException("A user with this email already exists.");
            }
            // The first attempt saved the account but the email never arrived (or the page was closed):
            // send a fresh code instead of telling the owner the application already exists.
            if (application.Status == GymApplicationStatus.Pending && !user.IsEmailVerified)
            {
                await ResendVerificationAsync(new ResendVerificationRequest { Email = user.Email });
                return new RegisterGymOwnerResult(
                    "Your application is saved. We sent a new 6-digit code to verify your email.",
                    user.Email,
                    EmailVerificationRequired: true);
            }
            if (application.Status != GymApplicationStatus.Rejected)
            {
                throw new InvalidOperationException(application.Status == GymApplicationStatus.Pending
                    ? "An application for this email is already awaiting review."
                    : "This gym owner account is already approved. Please sign in.");
            }

            var errors = GymApplicationValidator.ValidateGymDetails(input);
            if (errors.Count > 0) throw new GymApplicationValidationException(errors);

            var oldFiles = AllUrls(application);
            var uploaded = new List<string>();
            try
            {
                var fresh = await UploadApplicationAsync(input, request, uploaded);

                application.GymName            = fresh.GymName;
                application.OwnerRole          = fresh.OwnerRole;
                application.Description        = fresh.Description;
                application.Address            = fresh.Address;
                application.City               = fresh.City;
                application.GymPhone           = fresh.GymPhone;
                application.ContactEmail       = fresh.ContactEmail;
                application.Website            = fresh.Website;
                application.OpeningHours       = fresh.OpeningHours;
                application.Equipment          = fresh.Equipment;
                application.Classes            = fresh.Classes;
                application.GymPhotoUrls       = fresh.GymPhotoUrls;
                application.EquipmentPhotoUrls = fresh.EquipmentPhotoUrls;
                application.LicenseUrl         = fresh.LicenseUrl;
                application.Status             = GymApplicationStatus.Pending;
                application.ReviewNote         = null;
                application.ReviewedByUserId   = null;
                application.ReviewedAt         = null;
                application.UpdatedAt          = DateTime.UtcNow;

                await _dbContext.SaveChangesAsync();
            }
            catch
            {
                await DeleteUrlsAsync(uploaded);
                throw;
            }

            await DeleteUrlsAsync(oldFiles);

            return new RegisterGymOwnerResult(
                "Application re-submitted. We will email you once it has been reviewed.",
                user.Email,
                EmailVerificationRequired: false);
        }

        private async Task<GymApplication> UploadApplicationAsync(
            GymApplicationInput input, RegisterGymOwnerRequest request, List<string> uploaded)
        {
            var gymPhotos = new List<string>();
            foreach (var file in request.GymPhotos)
                gymPhotos.Add(await UploadAsync(file, "gym_photos", isDocument: false, uploaded));

            var equipmentPhotos = new List<string>();
            foreach (var file in request.EquipmentPhotos)
                equipmentPhotos.Add(await UploadAsync(file, "gym_equipment_photos", isDocument: false, uploaded));

            string? licenseUrl = null;
            if (request.License != null)
                licenseUrl = await UploadAsync(request.License, "gym_licences", isDocument: true, uploaded);

            return new GymApplication
            {
                GymName            = input.GymName.Trim(),
                OwnerRole          = GymApplicationValidator.OwnerRoles.First(r =>
                                         string.Equals(r, input.OwnerRole.Trim(), StringComparison.OrdinalIgnoreCase)),
                Description        = input.Description.Trim(),
                Address            = input.Address.Trim(),
                City               = input.City.Trim(),
                GymPhone           = input.GymPhone.Trim(),
                ContactEmail       = input.ContactEmail.Trim(),
                Website            = input.Website.Trim(),
                OpeningHours       = string.IsNullOrWhiteSpace(input.OpeningHours) ? null : input.OpeningHours.Trim(),
                Equipment          = GymApplicationValidator.CleanTags(input.Equipment).ToList(),
                Classes            = GymApplicationValidator.CleanTags(input.Classes).ToList(),
                GymPhotoUrls       = gymPhotos,
                EquipmentPhotoUrls = equipmentPhotos,
                LicenseUrl         = licenseUrl
            };
        }

        private async Task<string> UploadAsync(IFormFile file, string folder, bool isDocument, List<string> uploaded)
        {
            await using var stream = file.OpenReadStream();
            var url = await _imageService.UploadFileAsync(stream, file.FileName, folder, isDocument);
            uploaded.Add(url);
            return url;
        }

        /// <summary>Turns the posted form into the validator's input, reading each file's first bytes.</summary>
        private static async Task<GymApplicationInput> ToInputAsync(RegisterGymOwnerRequest request)
        {
            return new GymApplicationInput
            {
                FirstName       = request.FirstName ?? "",
                LastName        = request.LastName ?? "",
                Email           = request.Email ?? "",
                Phone           = request.Phone ?? "",
                Password        = request.Password ?? "",
                GymName         = request.GymName ?? "",
                OwnerRole       = request.OwnerRole ?? "",
                Description     = request.Description ?? "",
                Address         = request.Address ?? "",
                City            = request.City ?? "",
                GymPhone        = request.GymPhone ?? "",
                ContactEmail    = request.ContactEmail ?? "",
                Website         = request.Website ?? "",
                OpeningHours    = request.OpeningHours,
                Equipment       = request.Equipment ?? new List<string>(),
                Classes         = request.Classes ?? new List<string>(),
                GymPhotos       = await DescribeAsync(request.GymPhotos),
                EquipmentPhotos = await DescribeAsync(request.EquipmentPhotos),
                License         = request.License == null ? null : await DescribeAsync(request.License)
            };
        }

        private static async Task<IReadOnlyList<UploadedFileInfo>> DescribeAsync(IEnumerable<IFormFile>? files)
        {
            var result = new List<UploadedFileInfo>();
            foreach (var file in files ?? Array.Empty<IFormFile>())
                result.Add(await DescribeAsync(file));
            return result;
        }

        private static async Task<UploadedFileInfo> DescribeAsync(IFormFile file)
        {
            var header = new byte[16];
            await using var stream = file.OpenReadStream();
            var read = await stream.ReadAtLeastAsync(header, header.Length, throwOnEndOfStream: false);
            return new UploadedFileInfo(
                Path.GetFileName(file.FileName ?? "file"),
                file.ContentType ?? "",
                file.Length,
                header[..read]);
        }

        private Task<GymApplication?> GetGymApplicationAsync(User user) =>
            user.Role == UserRole.Gym_Owner
                ? _dbContext.GymApplications.SingleOrDefaultAsync(a => a.UserId == user.Id)
                : Task.FromResult<GymApplication?>(null);

        /// <summary>
        /// Owners who applied through the website must be approved first. Owners created directly by an admin
        /// have no application and are not affected.
        /// </summary>
        private async Task EnsureGymOwnerApprovedAsync(User user)
        {
            var application = await GetGymApplicationAsync(user);
            if (application != null && application.Status != GymApplicationStatus.Approved)
            {
                throw new GymOwnerNotApprovedException(application.Status, application.ReviewNote);
            }
        }

        private static List<string> AllUrls(GymApplication application)
        {
            var urls = new List<string>();
            urls.AddRange(application.GymPhotoUrls);
            urls.AddRange(application.EquipmentPhotoUrls);
            if (!string.IsNullOrWhiteSpace(application.LicenseUrl)) urls.Add(application.LicenseUrl);
            return urls;
        }

        private async Task DeleteUrlsAsync(IEnumerable<string> urls)
        {
            foreach (var url in urls)
            {
                try
                {
                    await _imageService.DeleteImageAsync(url);
                }
                catch
                {
                    // Cleanup is best effort; never fail the request over an external file.
                }
            }
        }
    }
}
