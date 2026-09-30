using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using VitroFit.API.Features.AdaptiveFitness;

namespace VitroFit.API.Features.AdaptiveFitness.Data.Migrations;

[DbContext(typeof(FitnessDbContext))]
[Migration("20260927123000_AddAdaptiveFitnessCycles")]
public sealed class AddAdaptiveFitnessCycles : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "Cycles",
            schema: "fitness",
            columns: table => new
            {
                Id = table.Column<Guid>(type: "uuid", nullable: false),
                UserId = table.Column<int>(type: "integer", nullable: false),
                SourceWorkflowId = table.Column<Guid>(type: "uuid", nullable: false),
                StartDate = table.Column<DateOnly>(type: "date", nullable: false),
                EndDate = table.Column<DateOnly>(type: "date", nullable: false),
                AnalysisJson = table.Column<string>(type: "jsonb", nullable: false),
                ScheduleJson = table.Column<string>(type: "jsonb", nullable: false),
                CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
            },
            constraints: table =>
            {
                table.PrimaryKey("PK_Cycles", x => x.Id);
                table.ForeignKey("FK_Cycles_Workflows_SourceWorkflowId", x => x.SourceWorkflowId,
                    principalSchema: "fitness", principalTable: "Workflows", principalColumn: "Id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateIndex("IX_Cycles_SourceWorkflowId", "Cycles", "SourceWorkflowId", schema: "fitness", unique: true);
        migrationBuilder.CreateIndex("IX_Cycles_UserId_StartDate", "Cycles", new[] { "UserId", "StartDate" }, schema: "fitness");
    }

    protected override void Down(MigrationBuilder migrationBuilder)
        => migrationBuilder.DropTable(name: "Cycles", schema: "fitness");
}
