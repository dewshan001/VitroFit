namespace VitroFit.API.Services
{
    public interface IImageService
    {
        Task<string> UploadProfileImageAsync(Stream fileStream, string fileName, string contentType);
        Task DeleteImageAsync(string imageUrl);
    }
}
