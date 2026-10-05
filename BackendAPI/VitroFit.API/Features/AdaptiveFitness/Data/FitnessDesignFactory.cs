using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
namespace VitroFit.API.Features.AdaptiveFitness;

// Scaffolding must not start the existing API or its sidecars.
public sealed class FitnessDesignFactory : IDesignTimeDbContextFactory<FitnessDbContext>
{
    public FitnessDbContext CreateDbContext(string[] args)
    {
        // design-time (dotnet ef) never runs Program.cs, so load the shared BackendAPI/.env here too
        for (var dir = new DirectoryInfo(Directory.GetCurrentDirectory()); dir != null; dir = dir.Parent)
        {
            var envFile = Path.Combine(dir.FullName, ".env");
            if (File.Exists(envFile)) { DotNetEnv.Env.NoClobber().Load(envFile); break; }
        }
        var config = new ConfigurationBuilder().SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile("appsettings.json", optional: true).AddEnvironmentVariables().Build();
        var options = new DbContextOptionsBuilder<FitnessDbContext>().UseNpgsql(
            config.GetConnectionString("DefaultConnection") ?? "Host=localhost;Database=VitroFit;Username=postgres",
            postgres => postgres.MigrationsHistoryTable("__FitnessMigrationsHistory", "fitness"));
        return new FitnessDbContext(options.Options);
    }
}
