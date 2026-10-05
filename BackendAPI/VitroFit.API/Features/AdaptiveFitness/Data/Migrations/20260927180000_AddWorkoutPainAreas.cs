using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using VitroFit.API.Features.AdaptiveFitness;

namespace VitroFit.API.Features.AdaptiveFitness.Data.Migrations;

[DbContext(typeof(FitnessDbContext))]
[Migration("20260927180000_AddWorkoutPainAreas")]
public sealed class AddWorkoutPainAreas : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<string[]>(
            name: "AffectedAreas",
            schema: "fitness",
            table: "Progress",
            type: "text[]",
            nullable: false,
            defaultValue: Array.Empty<string>());
    }

    protected override void Down(MigrationBuilder migrationBuilder)
        => migrationBuilder.DropColumn(name: "AffectedAreas", schema: "fitness", table: "Progress");
}
