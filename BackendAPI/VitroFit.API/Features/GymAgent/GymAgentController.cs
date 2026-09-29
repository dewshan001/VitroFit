using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace VitroFit.API.Features.GymAgent
{
    /// <summary>
    /// Public API for the gym multi-agent workflow (planner, gym analysis, workout recommendation,
    /// validator). Authentication and roles are enforced here; the Python service is internal.
    /// Any signed-in user may start a workflow and follow their own runs. Only Gym_Owner and Admin
    /// may see the approval queue and approve, reject or request revision of a run.
    /// </summary>
    [ApiController]
    [Route("api/gym-agent/workflows")]
    [Authorize]
    [TypeFilter(typeof(GymAgentExceptionFilter))]
    public class GymAgentController : ControllerBase
    {
        public const string ApproverRoles = "Gym_Owner,Admin";
        private static readonly string[] ApproverRoleList = ApproverRoles.Split(',');

        private readonly IGymAgentClient _agent;

        public GymAgentController(IGymAgentClient agent)
        {
            _agent = agent;
        }

        // The token's "sub" may surface as NameIdentifier or as "sub" depending on claim mapping
        // (see AuthController.GetUserId), and its role as ClaimTypes.Role or the raw "role".
        private string UserId =>
            User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue(JwtRegisteredClaimNames.Sub)
            ?? User.FindFirstValue("sub")
            ?? string.Empty;

        private string UserRole =>
            User.FindFirstValue(ClaimTypes.Role)
            ?? User.FindFirstValue("role")
            ?? string.Empty;
        private bool IsApprover => ApproverRoleList.Contains(UserRole);

        /// <summary>Start a workflow for one gym. The result waits for human approval before anything is published.</summary>
        [HttpPost]
        [ProducesResponseType(typeof(StartedWorkflowDto), StatusCodes.Status202Accepted)]
        public async Task<IActionResult> Start([FromBody] StartGymWorkflowRequest request, CancellationToken ct)
        {
            if (string.IsNullOrEmpty(UserId)) return Unauthorized();
            var started = await _agent.StartAsync(request, UserId, ct);
            return AcceptedAtAction(nameof(Get), new { id = started.Id }, started);
        }

        /// <summary>Workflows started by the caller. Approvers may pass ?all=true to see every run.</summary>
        [HttpGet]
        public async Task<IActionResult> List([FromQuery] string? status, [FromQuery] bool all = false, CancellationToken ct = default)
        {
            var requestedBy = all && IsApprover ? null : UserId;
            return Ok(await _agent.ListAsync(status, requestedBy, ct));
        }

        /// <summary>Runs waiting for a decision (approval queue).</summary>
        [HttpGet("pending")]
        [Authorize(Roles = ApproverRoles)]
        public async Task<IActionResult> Pending(CancellationToken ct)
            => Ok(await _agent.ListAsync("AwaitingApproval", null, ct));

        [HttpGet("{id}")]
        public async Task<IActionResult> Get(string id, CancellationToken ct)
        {
            var workflow = await _agent.GetAsync(id, ct);
            return CanView(workflow) ? Ok(workflow) : NotFound();
        }

        /// <summary>Auditable execution summary: each agent and tool step with timing and outcome.</summary>
        [HttpGet("{id}/events")]
        public async Task<IActionResult> Events(string id, CancellationToken ct)
        {
            var workflow = await _agent.GetAsync(id, ct);
            if (!CanView(workflow)) return NotFound();
            return Ok(await _agent.GetEventsAsync(id, ct));
        }

        [HttpPost("{id}/approve")]
        [Authorize(Roles = ApproverRoles)]
        public Task<IActionResult> Approve(string id, [FromBody] ReviewRequest? review, CancellationToken ct)
            => Decide(id, "approve", review, ct);

        [HttpPost("{id}/reject")]
        [Authorize(Roles = ApproverRoles)]
        public Task<IActionResult> Reject(string id, [FromBody] ReviewRequest? review, CancellationToken ct)
            => Decide(id, "reject", review, ct);

        /// <summary>Send the run back to the agents with the reviewer's feedback (a reason is required).</summary>
        [HttpPost("{id}/revise")]
        [Authorize(Roles = ApproverRoles)]
        public Task<IActionResult> Revise(string id, [FromBody] ReviewRequest? review, CancellationToken ct)
            => Decide(id, "revise", review, ct);

        private async Task<IActionResult> Decide(string id, string decision, ReviewRequest? review, CancellationToken ct)
        {
            var reason = review?.Reason?.Trim();
            if (decision == "revise" && string.IsNullOrEmpty(reason))
            {
                ModelState.AddModelError(nameof(ReviewRequest.Reason), "A reason is required to request a revision.");
                return ValidationProblem(ModelState);
            }

            await _agent.DecideAsync(id, new GymDecision(decision, reason, UserId, UserRole), ct);
            return Accepted(new { id, decision });
        }

        private bool CanView(GymWorkflowDto workflow)
            => IsApprover || workflow.RequestedBy == UserId;
    }
}
