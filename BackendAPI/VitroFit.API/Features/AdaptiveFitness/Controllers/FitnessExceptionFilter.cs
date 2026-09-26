using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.EntityFrameworkCore;

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
        context.Result = new ObjectResult(new { message = conflict
            ? "This record changed. Refresh and try again."
            : "Fitness unavailable. Check the API log using this request ID.", traceId })
            { StatusCode = conflict ? 409 : 503 };
        context.ExceptionHandled = true;
    }
}
