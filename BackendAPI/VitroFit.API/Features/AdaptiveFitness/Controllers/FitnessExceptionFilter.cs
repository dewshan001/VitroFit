using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace VitroFit.API.Features.AdaptiveFitness;

public sealed class FitnessExceptionFilter(ILogger<FitnessExceptionFilter> logger) : IExceptionFilter
{
    public void OnException(ExceptionContext context)
    {
        var conflict = context.Exception is DbUpdateConcurrencyException;
        var traceId = context.HttpContext.TraceIdentifier;
        if (conflict)
            logger.LogWarning(context.Exception, "Fitness request conflict. TraceId={TraceId}", traceId);
        else
            logger.LogError(context.Exception, "Fitness request failed. TraceId={TraceId}", traceId);

        var diagnostic = conflict
            ? new FitnessFailure("RECORD_CHANGED", "This record changed. Refresh and try again.", null)
            : GetSafeDiagnostic(context.Exception);
        context.Result = new ObjectResult(new
            { code = diagnostic.Code, message = diagnostic.Message, action = diagnostic.Action, traceId })
            { StatusCode = conflict ? 409 : 503 };
        context.ExceptionHandled = true;
    }

    private static FitnessFailure GetSafeDiagnostic(Exception exception)
    {
        for (Exception? current = exception; current is not null; current = current.InnerException)
        {
            if (current is PostgresException postgres)
            {
                return postgres.SqlState switch
                {
                    "42P01" or "42703" or "3F000" => new("FITNESS_MIGRATION_MISSING",
                        "The fitness database schema or a required table is missing.",
                        "Stop the API, run `dotnet ef database update --context FitnessDbContext` from BackendAPI/VitroFit.API, then restart the API."),
                    "28P01" => new("DATABASE_AUTH_FAILED",
                        "PostgreSQL rejected the database credentials.",
                        "Check ConnectionStrings:DefaultConnection in your local configuration."),
                    "08001" or "08006" or "57P03" => new("DATABASE_UNAVAILABLE",
                        "The fitness database could not be reached.",
                        "Confirm PostgreSQL is running and ConnectionStrings:DefaultConnection points to the correct database."),
                    _ => new("DATABASE_REQUEST_FAILED",
                        "The fitness database could not complete this request.",
                        "Check the API log using the request ID below; it contains the database error details.")
                };
            }

            if (current is HttpRequestException { StatusCode: { } status })
            {
                return status == System.Net.HttpStatusCode.Unauthorized
                    ? new("FITNESS_AGENT_AUTH_FAILED", "The fitness agent rejected the API request.",
                        "Make sure FITNESS_SERVICE_KEY and FitnessAgent:ServiceKey match, then restart both services.")
                    : new("FITNESS_AGENT_HTTP_ERROR", $"The fitness agent returned HTTP {(int)status}.",
                        "Check the Python agent log and its configuration.");
            }

            if (current is HttpRequestException)
                return new("FITNESS_AGENT_UNREACHABLE", "The fitness agent could not be reached.",
                    "Confirm the Python agent is running at FitnessAgent:BaseUrl (normally http://127.0.0.1:8002). Check its log for startup errors.");

            if (current is OperationCanceledException)
                return new("FITNESS_AGENT_TIMEOUT", "The fitness agent did not finish before the request timed out.",
                    "Check the Python agent log and provider availability, then retry.");

            if (current is InvalidOperationException && current.Message == "Fitness service is not configured.")
                return new("FITNESS_AGENT_NOT_CONFIGURED", "The fitness service key is not configured in ASP.NET.",
                    "Set FitnessAgent:ServiceKey to the same 32-character-or-longer key as FITNESS_SERVICE_KEY, then restart the API.");
        }

        return new("FITNESS_REQUEST_FAILED", "The fitness request could not be completed.",
            "Use the request ID below to find the full exception in the API console log.");
    }

    private sealed record FitnessFailure(string Code, string Message, string? Action);
}
