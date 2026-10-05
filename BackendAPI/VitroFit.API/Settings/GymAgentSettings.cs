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

        /// <summary>Timeout for quick calls (status, lists, decisions).</summary>
        public int TimeoutSeconds { get; set; } = 30;

        /// <summary>Timeout for calls that run the LLM (gym details, workout suggestions). Enrichment can take a minute or two.</summary>
        public int AiTimeoutSeconds { get; set; } = 150;

        /// <summary>Per-user (per-IP when anonymous) limit on calls that can start LLM work.</summary>
        public int AiRequestsPerMinute { get; set; } = 60;
    }
}
