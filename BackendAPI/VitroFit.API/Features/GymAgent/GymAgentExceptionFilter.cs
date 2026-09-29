using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

namespace VitroFit.API.Features.GymAgent
{
    /// <summary>Turns GymAgentException into a ProblemDetails response with the mapped status code.</summary>
    public sealed class GymAgentExceptionFilter : IExceptionFilter
    {
        public void OnException(ExceptionContext context)
        {
            if (context.Exception is not GymAgentException ex) return;

            context.Result = new ObjectResult(new ProblemDetails
            {
                Status = (int)ex.Status,
                Title = "Gym agent request failed",
                Detail = ex.Message
            })
            { StatusCode = (int)ex.Status };
            context.ExceptionHandled = true;
        }
    }
}
