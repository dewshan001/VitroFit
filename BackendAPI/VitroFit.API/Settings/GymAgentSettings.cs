namespace VitroFit.API.Settings
{
    /// <summary>
    /// Connection to the internal Python gym-workflow service. React and Flutter never call it;
    /// only this API does. <see cref="ServiceKey"/> is a secret: set it with user-secrets or the
    /// GymAgent__ServiceKey environment variable, never in a committed file.
    /// </summary>
    public sealed class GymAgentSettings
    {
        public const string SectionName = "GymAgent";

        public string BaseUrl { get; set; } = "http://127.0.0.1:8001";

        /// <summary>Shared secret sent as X-Gym-Agent-Key (minimum 32 characters).</summary>
        public string ServiceKey { get; set; } = string.Empty;

        public int TimeoutSeconds { get; set; } = 30;
    }
}
