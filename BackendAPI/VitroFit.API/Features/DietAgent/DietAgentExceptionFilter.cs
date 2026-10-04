using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

namespace VitroFit.API.Features.DietAgent
{
    /// <summary>
    /// Turns DietAgentException into a ProblemDetails response with the mapped status code. The web app reads the
    /// error text from <c>detail</c>, which ProblemDetails also uses, so the message shows the same way as any diet error.
    /// </summary>
    public sealed class DietAgentExceptionFilter : IExceptionFilter
    {
        public void OnException(ExceptionContext context)
        {
            if (context.Exception is not DietAgentException ex) return;

            context.Result = new ObjectResult(new ProblemDetails
            {
                Status = (int)ex.Status,
                Title = "Diet plan request failed",
                Detail = ex.Message
            })
            { StatusCode = (int)ex.Status };
            context.ExceptionHandled = true;
        }
    }
}
