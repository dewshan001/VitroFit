namespace VitroFit.API.Settings
{
    /// <summary>
    /// Strongly-typed configuration for SMTP email delivery.
    /// Values are bound from the "EmailSettings" section in appsettings.json.
    /// </summary>
    public sealed class EmailSettings
    {
        /// <summary>SMTP server hostname (e.g. smtp.gmail.com)</summary>
        public string Host { get; set; } = string.Empty;

        /// <summary>SMTP port — typically 587 for STARTTLS or 465 for SSL.</summary>
        public int Port { get; set; } = 587;

        /// <summary>
        /// Whether to use SSL/TLS on connect.
        /// Set to false for STARTTLS (port 587); true for direct SSL (port 465).
        /// </summary>
        public bool UseSsl { get; set; } = false;

        /// <summary>SMTP login username (usually your email address).</summary>
        public string Username { get; set; } = string.Empty;

        /// <summary>
        /// SMTP login password.
        /// For Gmail, this must be an App Password — NOT your Google account password.
        /// Generate one at https://myaccount.google.com/apppasswords
        /// </summary>
        public string Password { get; set; } = string.Empty;

        /// <summary>Human-readable display name shown in the From field.</summary>
        public string SenderName { get; set; } = "VitroFit";

        /// <summary>Email address shown in the From field.</summary>
        public string SenderEmail { get; set; } = string.Empty;
    }
}
