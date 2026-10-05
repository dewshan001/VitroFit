using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace VitroFit.API.Features.GymAgent
{
    /// <summary>
    /// Public API for the gym multi-agent workflow (planner, gym analysis, workout recommendation,
    /// validator). Authentication and roles are enforced here; the Python service is internal.
    /// Any signed-in user may follow their own runs. Admins see and decide every run. A Gym_Owner is
    /// scoped to the runs they started themselves (their own gym), so an approved owner can never see or
    /// decide another owner's run.
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
        private bool IsAdmin => UserRole == "Admin";

        /// <summary>
        /// Start a workflow for one gym (Admin or Gym_Owner). Each run uses the LLM, so it is limited by role and
        /// rate; the result waits for human approval before anything is published.
        /// </summary>
        [HttpPost]
        [Authorize(Roles = ApproverRoles)]
        [Microsoft.AspNetCore.RateLimiting.EnableRateLimiting(GymAgentRateLimiting.PolicyName)]
        [ProducesResponseType(typeof(StartedWorkflowDto), StatusCodes.Status202Accepted)]
        public async Task<IActionResult> Start([FromBody] StartGymWorkflowRequest request, CancellationToken ct)
        {
            if (string.IsNullOrEmpty(UserId)) return Unauthorized();
            var started = await _agent.StartAsync(request, UserId, ct);
            return AcceptedAtAction(nameof(Get), new { id = started.Id }, started);
        }

        /// <summary>Workflows started by the caller. Admins may pass ?all=true to see every run.</summary>
        [HttpGet]
        public async Task<IActionResult> List([FromQuery] string? status, [FromQuery] bool all = false, CancellationToken ct = default)
        {
            var requestedBy = all && IsAdmin ? null : UserId;
            return Ok(await _agent.ListAsync(status, requestedBy, ct));
        }

        /// <summary>Runs waiting for a decision: every run for admins, only the caller's own for owners.</summary>
        [HttpGet("pending")]
        [Authorize(Roles = ApproverRoles)]
        public async Task<IActionResult> Pending(CancellationToken ct)
            => Ok(await _agent.ListAsync("AwaitingApproval", IsAdmin ? null : UserId, ct));

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

            // An owner may only decide runs they started; anything else looks like it does not exist.
            if (!IsAdmin && !CanView(await _agent.GetAsync(id, ct))) return NotFound();

            await _agent.DecideAsync(id, new GymDecision(decision, reason, UserId, UserRole), ct);
            return Accepted(new { id, decision });
        }

        private bool CanView(GymWorkflowDto workflow)
            => IsAdmin || workflow.RequestedBy == UserId;
    }
}
