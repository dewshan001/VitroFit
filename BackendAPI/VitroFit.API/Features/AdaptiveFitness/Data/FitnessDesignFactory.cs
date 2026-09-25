using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
namespace VitroFit.API.Features.AdaptiveFitness;

// Scaffolding must not start the existing API or its sidecars.
public sealed class FitnessDesignFactory : IDesignTimeDbContextFactory<FitnessDbContext>
{
    public FitnessDbContext CreateDbContext(string[] args)
    {
        var config = new ConfigurationBuilder().SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile("appsettings.json", optional: true).AddEnvironmentVariables().Build();
        var options = new DbContextOptionsBuilder<FitnessDbContext>().UseNpgsql(
            config.GetConnectionString("DefaultConnection") ?? "Host=localhost;Database=VitroFit;Username=postgres",
            postgres => postgres.MigrationsHistoryTable("__FitnessMigrationsHistory", "fitness"));
        return new FitnessDbContext(options.Options);
    }
}
