using MailKit.Net.Smtp;
using MailKit.Security;
using Microsoft.Extensions.Options;
using MimeKit;
using VitroFit.API.Settings;

namespace VitroFit.API.Services
{
    /// <summary>
    /// Concrete implementation of <see cref="IEmailService"/> that delivers emails
    /// via SMTP using the MailKit library.
    ///
    /// Configuration is injected from appsettings.json → EmailSettings.
    /// For Gmail, make sure to:
    ///   1. Enable 2-Step Verification on your Google account.
    ///   2. Generate an App Password at https://myaccount.google.com/apppasswords
    ///   3. Use that App Password (not your normal password) in appsettings.json.
    /// </summary>
    public sealed class MailKitEmailService : IEmailService
    {
        private readonly EmailSettings _emailSettings;
        private readonly ILogger<MailKitEmailService> _logger;

        public MailKitEmailService(
            IOptions<EmailSettings> emailOptions,
            ILogger<MailKitEmailService> logger)
        {
            _emailSettings = emailOptions.Value;
            _logger = logger;
        }

        /// <summary>
        /// Builds a MIME message and delivers it over an authenticated SMTP connection.
        /// Uses STARTTLS (SecureSocketOptions.StartTls) which is the standard for port 587.
        /// </summary>
        public async Task SendAsync(string toEmail, string toName, string subject, string htmlBody)
        {
            // --- 1. Build the MIME message ---
            var message = new MimeMessage();

            // From: "VitroFit" <noreply@yourdomain.com>
            message.From.Add(new MailboxAddress(_emailSettings.SenderName, _emailSettings.SenderEmail));

            // To: recipient
            message.To.Add(new MailboxAddress(toName, toEmail));

            message.Subject = subject;

            // Build a multipart body that includes both HTML and a plain-text fallback.
            // Email clients that can't render HTML will show the plain-text part instead.
            var bodyBuilder = new BodyBuilder
            {
                HtmlBody  = htmlBody,
                TextBody  = "Please view this email in an HTML-compatible email client."
            };

            message.Body = bodyBuilder.ToMessageBody();

            // --- 2. Connect, authenticate, and send ---
            using var smtp = new SmtpClient();

            try
            {
                // Connect using STARTTLS (upgrades the connection to TLS after initial handshake).
                // SecureSocketOptions.StartTls is the correct option for port 587.
                // If you switch to port 465, change this to SecureSocketOptions.SslOnConnect.
                var secureOption = _emailSettings.UseSsl
                    ? SecureSocketOptions.SslOnConnect      // port 465
                    : SecureSocketOptions.StartTls;          // port 587

                await smtp.ConnectAsync(_emailSettings.Host, _emailSettings.Port, secureOption);

                // Authenticate with the SMTP server using the credentials from appsettings.json.
                await smtp.AuthenticateAsync(_emailSettings.Username, _emailSettings.Password);

                // Send the assembled message.
                await smtp.SendAsync(message);

                _logger.LogInformation("Email sent successfully to {ToEmail}", toEmail);
            }
            catch (Exception ex)
            {
                // Log the error but don't expose SMTP details to the caller.
                _logger.LogError(ex, "Failed to send email to {ToEmail}", toEmail);
                throw new InvalidOperationException("Failed to send the email. Please try again later.", ex);
            }
            finally
            {
                // Always disconnect cleanly from the SMTP server.
                await smtp.DisconnectAsync(true);
            }
        }
    }
}
