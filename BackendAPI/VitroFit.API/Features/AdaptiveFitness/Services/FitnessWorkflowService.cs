using Microsoft.EntityFrameworkCore;

namespace VitroFit.API.Features.AdaptiveFitness;

public sealed class FitnessWorkflowService(FitnessDbContext db, FitnessAgentClient agent,
    ILogger<FitnessWorkflowService> logger)
{
    public async Task Run(FitnessWorkflow workflow)
    {
        var request = FitnessJson.Read<AgentRequest>(workflow.RequestJson);
        try
        {
            // The run survives browser disconnection; service timeout still bounds its lifetime.
            var result = await agent.Generate(request, CancellationToken.None);
            if (result.Status is not ("Ready" or "ReviewRequired" or "Failed"))
                throw new InvalidOperationException("Invalid agent status.");
            var errors = result.Status == "Ready" ? FitnessPolicy.Validate(result.Plan, request) : [];
            workflow.Status = errors.Count == 0 ? result.Status : "Failed";
            workflow.PlanJson = workflow.Status == "Ready" ? FitnessJson.Write(result.Plan) : null;
            workflow.Summary = errors.Count > 0 ? string.Join(" ", errors) : result.Status == "Failed" && result.Errors.Count > 0
                ? "Planning failed after the retry limit: " + string.Join(" ", result.Errors)
                : result.Status == "ReviewRequired"
                ? "Your answers indicate a possible safety concern. The self-scheduling agent cannot assess medical readiness. Please get appropriate professional guidance before continuing." : result.Status == "Failed"
                ? "Planning failed within the retry limit; no plan activated." : result.Analysis;
        }
        catch (Exception ex)
        {
            // Log only the exception type, never request bodies, credentials or provider responses.
            var reason = ex switch
            {
                HttpRequestException { StatusCode: { } status } => $"The Python agent returned HTTP {(int)status}.",
                HttpRequestException => "The Python agent could not be reached.",
                OperationCanceledException => "The Python agent request timed out or was cancelled.",
                _ => "The agent workflow failed before it returned a plan."
            };
            logger.LogWarning("Fitness workflow {WorkflowId} failed ({ErrorType})", workflow.Id, ex.GetType().Name);
            workflow.Status = "Failed";
            workflow.PlanJson = null;
            workflow.Summary = $"{reason} No plan was activated. Check the Python agent logs and service configuration, then retry.";
        }
        workflow.CurrentStep = workflow.Status == "Ready" ? "self_schedule_ready" : "finished";
        workflow.UpdatedAt = DateTime.UtcNow;
        workflow.Version++;
        db.Events.Add(new() { WorkflowId = workflow.Id, Step = workflow.CurrentStep, Summary = workflow.Summary });
        await db.SaveChangesAsync();
    }
}
