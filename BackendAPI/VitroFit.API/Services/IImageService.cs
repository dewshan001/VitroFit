namespace VitroFit.API.Services
{
    public interface IImageService
    {
        Task<string> UploadProfileImageAsync(Stream fileStream, string fileName, string contentType);

        /// <summary>
        /// Uploads a file into the given Cloudinary folder (e.g. "gym_photos"). Documents such as PDFs
        /// are stored as raw files; images are stored as images. Returns the secure URL.
        /// </summary>
        Task<string> UploadFileAsync(Stream fileStream, string fileName, string folder, bool isDocument);

        Task DeleteImageAsync(string imageUrl);
    }
}
