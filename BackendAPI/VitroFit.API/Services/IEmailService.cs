namespace VitroFit.API.Services
{
    /// <summary>
    /// Abstraction for sending outbound emails.
    /// Keeping this as an interface allows easy swapping of providers
    /// (e.g. switching from SMTP to SendGrid) without touching business logic.
    /// </summary>
    public interface IEmailService
    {
        /// <summary>
        /// Sends an email to a single recipient.
        /// </summary>
        /// <param name="toEmail">Recipient email address.</param>
        /// <param name="toName">Recipient display name.</param>
        /// <param name="subject">Email subject line.</param>
        /// <param name="htmlBody">Full HTML content of the email body.</param>
        Task SendAsync(string toEmail, string toName, string subject, string htmlBody);
    }
}
