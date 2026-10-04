namespace VitroFit.API.Settings
{
    /// <summary>
    /// Connection to the Python diet-plan service. Browsers call this API (api/diet/*); only this API calls the
    /// service. <see cref="ServiceKey"/> is a secret: set it with user-secrets or the DietAgent__ServiceKey
    /// environment variable, never in a committed file, and give the service the same value as DIET_AGENT_KEY.
    /// </summary>
    public sealed class DietAgentSettings
    {
        public const string SectionName = "DietAgent";

        public string BaseUrl { get; set; } = "http://127.0.0.1:8003";

        /// <summary>
        /// Shared secret sent as X-Diet-Agent-Key (minimum 32 characters). Empty means "the service is not in
        /// internal-only mode yet": no header is sent, which is how the service behaved before the key existed.
        /// </summary>
        public string ServiceKey { get; set; } = string.Empty;

        /// <summary>Timeout for every call. Generating and editing a plan return at once (the service works in the background), so this is short.</summary>
        public int TimeoutSeconds { get; set; } = 30;

        /// <summary>Per-user (per-IP when anonymous) limit on the calls that start LLM work: generating and editing a plan.</summary>
        public int AiRequestsPerMinute { get; set; } = 20;
    }
}
