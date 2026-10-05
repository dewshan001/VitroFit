using CloudinaryDotNet;
using CloudinaryDotNet.Actions;
using Microsoft.Extensions.Options;
using VitroFit.API.Settings;

namespace VitroFit.API.Services
{
    public sealed class CloudinaryImageService : IImageService
    {
        private readonly Cloudinary _cloudinary;

        public CloudinaryImageService(IOptions<CloudinarySettings> options)
        {
            var settings = options.Value;
            var account = new Account(settings.CloudName, settings.ApiKey, settings.ApiSecret);
            _cloudinary = new Cloudinary(account)
            {
                Api = { Secure = true }
            };
        }

        public async Task<string> UploadProfileImageAsync(Stream fileStream, string fileName, string contentType)
        {
            fileStream.Position = 0;

            var safeName = Path.GetFileNameWithoutExtension(fileName)?.Replace(' ', '_') ?? "profile_image";
            var uploadParams = new ImageUploadParams
            {
                File = new FileDescription(fileName, fileStream),
                PublicId = $"vitrofit/profile_images/{safeName}_{Guid.NewGuid():N}",
                Overwrite = false
            };

            var result = await _cloudinary.UploadAsync(uploadParams);
            if (result.StatusCode != System.Net.HttpStatusCode.OK && result.StatusCode != System.Net.HttpStatusCode.Created)
            {
                throw new InvalidOperationException("Failed to upload image to Cloudinary.");
            }

            return result.SecureUrl?.ToString() ?? string.Empty;
        }

        public async Task<string> UploadFileAsync(Stream fileStream, string fileName, string folder, bool isDocument)
        {
            fileStream.Position = 0;

            // The public id never reuses the client file name, so uploaded names cannot be guessed or abused.
            var publicId = $"vitrofit/{folder}/{Guid.NewGuid():N}";
            var extension = Path.GetExtension(fileName);

            UploadResult result;
            if (isDocument)
            {
                // Raw resources keep their extension in the public id so the URL opens as the right file type.
                result = await _cloudinary.UploadAsync(new RawUploadParams
                {
                    File = new FileDescription(fileName, fileStream),
                    PublicId = publicId + extension,
                    Overwrite = false
                });
            }
            else
            {
                result = await _cloudinary.UploadAsync(new ImageUploadParams
                {
                    File = new FileDescription(fileName, fileStream),
                    PublicId = publicId,
                    Overwrite = false
                });
            }

            if (result.StatusCode != System.Net.HttpStatusCode.OK && result.StatusCode != System.Net.HttpStatusCode.Created)
            {
                throw new InvalidOperationException("Failed to upload the file to Cloudinary.");
            }

            return result.SecureUrl?.ToString() ?? string.Empty;
        }

        public async Task DeleteImageAsync(string imageUrl)
        {
            if (string.IsNullOrWhiteSpace(imageUrl))
                return;

            var isRaw = imageUrl.Contains("/raw/upload/", StringComparison.OrdinalIgnoreCase);
            var publicId = ExtractPublicId(imageUrl);
            if (string.IsNullOrWhiteSpace(publicId))
                return;

            var deleteParams = new DeletionParams(publicId)
            {
                ResourceType = isRaw ? ResourceType.Raw : ResourceType.Image
            };
            await _cloudinary.DestroyAsync(deleteParams);
        }

        private static string? ExtractPublicId(string imageUrl)
        {
            if (string.IsNullOrWhiteSpace(imageUrl)) return null;

            if (!imageUrl.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
                !imageUrl.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            {
                return imageUrl;
            }

            try
            {
                var uri = new Uri(imageUrl);
                var path = uri.AbsolutePath;

                var marker = path.Contains("/raw/upload/", StringComparison.OrdinalIgnoreCase)
                    ? "/raw/upload/"
                    : "/image/upload/";
                int uploadIndex = path.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
                if (uploadIndex == -1) return null;

                var relativePath = path.Substring(uploadIndex + marker.Length);

                if (System.Text.RegularExpressions.Regex.IsMatch(relativePath, @"^v\d+/"))
                {
                    relativePath = System.Text.RegularExpressions.Regex.Replace(relativePath, @"^v\d+/", "");
                }

                // Image public ids exclude the extension; raw public ids include it.
                int lastDotIndex = relativePath.LastIndexOf('.');
                if (lastDotIndex > 0 && marker == "/image/upload/")
                {
                    relativePath = relativePath.Substring(0, lastDotIndex);
                }

                return relativePath;
            }
            catch
            {
                return null;
            }
        }
    }
}
