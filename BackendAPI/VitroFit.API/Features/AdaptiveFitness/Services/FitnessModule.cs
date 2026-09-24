using Microsoft.EntityFrameworkCore;

namespace VitroFit.API.Features.AdaptiveFitness;

public static class FitnessModule
{
    public static IServiceCollection AddAdaptiveFitness(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddDbContext<FitnessDbContext>(options => options.UseNpgsql(
            configuration.GetConnectionString("DefaultConnection"),
            postgres => postgres.MigrationsHistoryTable("__FitnessMigrationsHistory", "fitness")));
        services.AddHttpClient<FitnessAgentClient>(client => {
            client.BaseAddress = new Uri(configuration["FitnessAgent:BaseUrl"] ?? "http://127.0.0.1:8002");
            client.Timeout = TimeSpan.FromSeconds(120);
        });
        services.AddScoped<FitnessWorkflowService>();
        return services;
    }
}

public sealed class FitnessAgentClient(HttpClient client, IConfiguration configuration)
{
    public async Task<AgentResult> Generate(AgentRequest request, CancellationToken cancellation)
    {
        var key = configuration["FitnessAgent:ServiceKey"];
        if (string.IsNullOrWhiteSpace(key) || key.Length < 32) throw new InvalidOperationException("Fitness service is not configured.");
        using var message = new HttpRequestMessage(HttpMethod.Post, "/internal/generate");
        message.Headers.Add("X-Fitness-Key", key);
        message.Content = JsonContent.Create(request);
        using var response = await client.SendAsync(message, cancellation);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<AgentResult>(cancellation)
            ?? throw new InvalidOperationException("Empty fitness response.");
    }
}
