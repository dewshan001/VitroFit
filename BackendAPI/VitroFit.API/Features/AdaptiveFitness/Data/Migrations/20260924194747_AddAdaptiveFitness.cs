using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace VitroFit.API.Features.AdaptiveFitness.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddAdaptiveFitness : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "fitness");

            migrationBuilder.CreateTable(
                name: "Exercises",
                schema: "fitness",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    Equipment = table.Column<string>(type: "text", nullable: false),
                    MuscleGroup = table.Column<string>(type: "text", nullable: false),
                    Instructions = table.Column<string>(type: "text", nullable: false),
                    BeginnerAllowed = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Exercises", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Profiles",
                schema: "fitness",
                columns: table => new
                {
                    UserId = table.Column<int>(type: "integer", nullable: false),
                    Age = table.Column<int>(type: "integer", nullable: false),
                    HeightCm = table.Column<double>(type: "double precision", nullable: false),
                    WeightKg = table.Column<double>(type: "double precision", nullable: false),
                    Goal = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    Days = table.Column<int[]>(type: "integer[]", nullable: false),
                    SessionMinutes = table.Column<int>(type: "integer", nullable: false),
                    Equipment = table.Column<string[]>(type: "text[]", nullable: false),
                    ReviewRequired = table.Column<bool>(type: "boolean", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Profiles", x => x.UserId);
                });

            migrationBuilder.CreateTable(
                name: "Workflows",
                schema: "fitness",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    UserId = table.Column<int>(type: "integer", nullable: false),
                    RunId = table.Column<Guid>(type: "uuid", nullable: false),
                    PreviousWorkflowId = table.Column<Guid>(type: "uuid", nullable: true),
                    Status = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    CurrentStep = table.Column<string>(type: "text", nullable: false),
                    RequestJson = table.Column<string>(type: "jsonb", nullable: false),
                    PlanJson = table.Column<string>(type: "jsonb", nullable: true),
                    Summary = table.Column<string>(type: "text", nullable: false),
                    Feedback = table.Column<string>(type: "text", nullable: false),
                    Version = table.Column<int>(type: "integer", nullable: false),
                    RevisionCount = table.Column<int>(type: "integer", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Workflows", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Workflows_Profiles_UserId",
                        column: x => x.UserId,
                        principalSchema: "fitness",
                        principalTable: "Profiles",
                        principalColumn: "UserId",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Workflows_Workflows_PreviousWorkflowId",
                        column: x => x.PreviousWorkflowId,
                        principalSchema: "fitness",
                        principalTable: "Workflows",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Approvals",
                schema: "fitness",
                columns: table => new
                {
                    Id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    WorkflowId = table.Column<Guid>(type: "uuid", nullable: false),
                    ReviewerId = table.Column<int>(type: "integer", nullable: false),
                    Version = table.Column<int>(type: "integer", nullable: false),
                    Decision = table.Column<string>(type: "text", nullable: false),
                    Reason = table.Column<string>(type: "text", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Approvals", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Approvals_Workflows_WorkflowId",
                        column: x => x.WorkflowId,
                        principalSchema: "fitness",
                        principalTable: "Workflows",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "Events",
                schema: "fitness",
                columns: table => new
                {
                    Id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    WorkflowId = table.Column<Guid>(type: "uuid", nullable: false),
                    Step = table.Column<string>(type: "text", nullable: false),
                    Summary = table.Column<string>(type: "text", nullable: false),
                    DurationMs = table.Column<int>(type: "integer", nullable: false),
                    SnapshotJson = table.Column<string>(type: "jsonb", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Events", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Events_Workflows_WorkflowId",
                        column: x => x.WorkflowId,
                        principalSchema: "fitness",
                        principalTable: "Workflows",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "Progress",
                schema: "fitness",
                columns: table => new
                {
                    Id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    WorkflowId = table.Column<Guid>(type: "uuid", nullable: false),
                    Day = table.Column<int>(type: "integer", nullable: false),
                    Completed = table.Column<bool>(type: "boolean", nullable: false),
                    Rpe = table.Column<int>(type: "integer", nullable: false),
                    Pain = table.Column<bool>(type: "boolean", nullable: false),
                    PerformedOn = table.Column<DateOnly>(type: "date", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Progress", x => x.Id);
                    table.CheckConstraint("CK_Progress_Day", "\"Day\" BETWEEN 1 AND 7");
                    table.CheckConstraint("CK_Progress_Rpe", "\"Rpe\" BETWEEN 1 AND 10");
                    table.ForeignKey(
                        name: "FK_Progress_Workflows_WorkflowId",
                        column: x => x.WorkflowId,
                        principalSchema: "fitness",
                        principalTable: "Workflows",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            // FitnessDbContext is deliberately separate from AppDbContext. Keep the user FK
            // pointed at the existing authoritative public.Users table without importing the
            // full auth/team model into fitness migrations.
            migrationBuilder.AddForeignKey(
                name: "FK_Profiles_Users_UserId",
                schema: "fitness",
                table: "Profiles",
                column: "UserId",
                principalSchema: "public",
                principalTable: "Users",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);

            migrationBuilder.InsertData(
                schema: "fitness",
                table: "Exercises",
                columns: new[] { "Id", "BeginnerAllowed", "Equipment", "Instructions", "MuscleGroup", "Name" },
                values: new object[,]
                {
                    { 1, true, "bodyweight", "Sit back to a stable chair and stand with control.", "legs", "Chair squat" },
                    { 2, true, "bodyweight", "Keep a straight body and press gently away from the wall.", "upper body", "Wall push-up" },
                    { 3, true, "bodyweight", "Hold a stable support and raise your heels slowly.", "legs", "Standing calf raise" },
                    { 4, true, "bodyweight", "Sit upright and straighten each knee with control.", "legs", "Seated knee extension" },
                    { 5, true, "bodyweight", "March gently in place; count one repetition per knee lift.", "full body", "Standing march" },
                    { 6, true, "dumbbells", "Use a comfortable light weight and keep elbows close to your sides.", "arms", "Light dumbbell curl" },
                    { 7, true, "resistance_band", "Use a secure band anchor and draw elbows back with control.", "back", "Seated band row" }
                });

            migrationBuilder.CreateIndex(
                name: "IX_Approvals_WorkflowId_Version",
                schema: "fitness",
                table: "Approvals",
                columns: new[] { "WorkflowId", "Version" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Events_WorkflowId_CreatedAt",
                schema: "fitness",
                table: "Events",
                columns: new[] { "WorkflowId", "CreatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_Exercises_Name",
                schema: "fitness",
                table: "Exercises",
                column: "Name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Progress_WorkflowId_Day",
                schema: "fitness",
                table: "Progress",
                columns: new[] { "WorkflowId", "Day" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Workflows_PreviousWorkflowId",
                schema: "fitness",
                table: "Workflows",
                column: "PreviousWorkflowId");

            migrationBuilder.CreateIndex(
                name: "IX_Workflows_Status",
                schema: "fitness",
                table: "Workflows",
                column: "Status");

            migrationBuilder.CreateIndex(
                name: "IX_Workflows_UserId_CreatedAt",
                schema: "fitness",
                table: "Workflows",
                columns: new[] { "UserId", "CreatedAt" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Approvals",
                schema: "fitness");

            migrationBuilder.DropTable(
                name: "Events",
                schema: "fitness");

            migrationBuilder.DropTable(
                name: "Exercises",
                schema: "fitness");

            migrationBuilder.DropTable(
                name: "Progress",
                schema: "fitness");

            migrationBuilder.DropTable(
                name: "Workflows",
                schema: "fitness");

            migrationBuilder.DropTable(
                name: "Profiles",
                schema: "fitness");
        }
    }
}
