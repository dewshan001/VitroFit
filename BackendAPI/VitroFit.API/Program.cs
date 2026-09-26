using System.Diagnostics;
using System.IdentityModel.Tokens.Jwt;
using System.Net.Sockets;
using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi;
using VitroFit.API.Data;
using VitroFit.API.Entities;
using VitroFit.API.Services;
using VitroFit.API.Settings;
using VitroFit.API.Features.AdaptiveFitness;

var builder = WebApplication.CreateBuilder(args);

// Clear default claim mapping so standard JWT claim names like 'sub' are retained
JwtSecurityTokenHandler.DefaultInboundClaimTypeMap.Clear();

// Add services to the container.

builder.Services.AddControllers();
builder.Services.AddAdaptiveFitness(builder.Configuration);
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Name = "Authorization",
        Type = SecuritySchemeType.Http,
        Scheme = "Bearer",
        BearerFormat = "JWT",
        In = ParameterLocation.Header,
        Description = "Enter 'Bearer' [space] and then your token in the text input below."
    });

    options.AddSecurityRequirement(doc => new OpenApiSecurityRequirement
    {
        [ new OpenApiSecuritySchemeReference("Bearer", doc, null) ] = new List<string>()
    });
});

builder.Services.AddCors(options =>
{
    options.AddPolicy("DefaultCorsPolicy", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

builder.Services.AddAuthorization();

builder.Services.Configure<JwtSettings>(builder.Configuration.GetSection("JwtSettings"));
builder.Services.Configure<CloudinarySettings>(builder.Configuration.GetSection("Cloudinary"));

// Bind SMTP settings from appsettings.json → EmailSettings section
builder.Services.Configure<EmailSettings>(builder.Configuration.GetSection("EmailSettings"));

builder.Services.AddSingleton<IImageService, CloudinaryImageService>();
builder.Services.AddScoped<ITokenService, TokenService>();
builder.Services.AddScoped<IAuthService, AuthService>();
builder.Services.AddScoped<IPasswordHasher<User>, PasswordHasher<User>>();

// Transient is appropriate for MailKitEmailService: each call opens and closes its own SMTP connection
builder.Services.AddTransient<IEmailService, MailKitEmailService>();

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection"))
           .ConfigureWarnings(w => w.Ignore(Microsoft.EntityFrameworkCore.Diagnostics.RelationalEventId.PendingModelChangesWarning)));

var jwtSettings = builder.Configuration.GetSection("JwtSettings").Get<JwtSettings>() ?? new JwtSettings();
var key = Encoding.UTF8.GetBytes(jwtSettings.Secret);

builder.Services.AddAuthentication(options =>
{
    options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(options =>
{
    options.RequireHttpsMetadata = false; // allow HTTP in development
    options.SaveToken = true;
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true,
        ValidateAudience = true,
        ValidateLifetime = true,
        ValidateIssuerSigningKey = true,
        ValidIssuer = jwtSettings.Issuer,
        ValidAudience = jwtSettings.Audience,
        IssuerSigningKey = new SymmetricSecurityKey(key),
        // Prevent ASP.NET Core from remapping 'sub' → ClaimTypes.NameIdentifier
        NameClaimType = JwtRegisteredClaimNames.Sub,
        RoleClaimType = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
    };
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseCors("DefaultCorsPolicy");
app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

using (var scope = app.Services.CreateScope())
{
    var context = scope.ServiceProvider.GetRequiredService<AppDbContext>();

    // Apply any pending EF Core migrations automatically (creates the DB on first run).
    context.Database.Migrate();

    var hasher = scope.ServiceProvider.GetRequiredService<IPasswordHasher<User>>();
    
    if (!context.Users.Any(u => u.Email == "admin@gmail.com"))
    {
        var admin = new User
        {
            FirstName = "System",
            LastName = "Admin",
            Email = "admin@gmail.com",
            Role = UserRole.Admin,
            IsEmailVerified = true
        };
        admin.PasswordHash = hasher.HashPassword(admin, "admin1234");
        context.Users.Add(admin);
        context.SaveChanges();
    }
}

var sidecarProcesses = new List<Process>();
foreach (var (serviceName, relativeDir, port, customArgs) in new (string, string, int, string?)[]
{
    ("GymAgentService", "GymAgentService", 8001, null),
    ("chatbot_service", "chatbot_service", 8000, null),
    ("DietPlanService", "DietPlanService", 8003, null),
    ("FitnessAgentService", "FitnessAgentService", 8002, "-m app.server"),
})
{
    var process = PythonServiceSidecar.StartIfAvailable(app.Logger, serviceName, relativeDir, port, customArgs);
    if (process != null)
    {
        sidecarProcesses.Add(process);
    }
}

if (sidecarProcesses.Count > 0)
{
    app.Lifetime.ApplicationStopping.Register(() =>
    {
        foreach (var process in sidecarProcesses)
        {
            PythonServiceSidecar.Stop(process, app.Logger);
        }
    });
}

app.Run();

/// <summary>
/// Launches a Python FastAPI sidecar service (GymAgentService, chatbot_service) alongside
/// the API, so it's available without a separate manual step. Purely best-effort: if
/// Python/the venv isn't set up yet, or the service is already running (e.g. started
/// manually), this logs and does nothing rather than failing backend startup.
/// </summary>
static class PythonServiceSidecar
{
    public static Process? StartIfAvailable(ILogger logger, string serviceName, string relativeDir, int port, string? customArgs = null)
    {
        if (IsPortInUse(port))
        {
            logger.LogInformation("{ServiceName} already listening on port {Port}, skipping sidecar launch.", serviceName, port);
            return null;
        }

        var apiProjectDir = Directory.GetCurrentDirectory();
        var serviceDir = Path.GetFullPath(Path.Combine(apiProjectDir, "..", relativeDir));
        var pythonExe = OperatingSystem.IsWindows()
            ? Path.Combine(serviceDir, "venv", "Scripts", "python.exe")
            : Path.Combine(serviceDir, "venv", "bin", "python");

        if (!File.Exists(pythonExe))
        {
            logger.LogWarning(
                "{ServiceName} venv not found at {PythonExe} - skipping auto-start. " +
                "Set it up with: cd BackendAPI/{RelativeDir} && python -m venv venv && " +
                "venv/Scripts/pip install -r requirements.txt (see .env.example for required settings).",
                serviceName, pythonExe, relativeDir);
            return null;
        }

        try
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = customArgs ?? $"-m uvicorn main:app --port {port}",
                WorkingDirectory = serviceDir,
                UseShellExecute = false,
                CreateNoWindow = true,
            };

            var process = Process.Start(startInfo);
            logger.LogInformation("Started {ServiceName} sidecar (pid {Pid}) on port {Port}.", serviceName, process?.Id, port);
            return process;
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Failed to start {ServiceName} sidecar.", serviceName);
            return null;
        }
    }

    public static void Stop(Process process, ILogger logger)
    {
        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
            }
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Failed to stop sidecar process.");
        }
    }

    private static bool IsPortInUse(int port)
    {
        try
        {
            using var client = new TcpClient();
            var connectTask = client.ConnectAsync("127.0.0.1", port);
            return connectTask.Wait(TimeSpan.FromMilliseconds(300)) && client.Connected;
        }
        catch
        {
            return false;
        }
    }
}
