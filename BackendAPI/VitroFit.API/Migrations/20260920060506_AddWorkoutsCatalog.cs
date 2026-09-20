using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace VitroFit.API.Migrations
{
    /// <inheritdoc />
    public partial class AddWorkoutsCatalog : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Workouts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    Category = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    Description = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Workouts", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Workouts_Name",
                table: "Workouts",
                column: "Name",
                unique: true);

            // Seed the shared workout catalog before wiring up TimetableSlots.WorkoutId,
            // so the default value below (and any pre-existing rows) reference a real workout.
            migrationBuilder.InsertData(
                table: "Workouts",
                columns: new[] { "Id", "Name", "Category", "Description" },
                values: new object[,]
                {
                    { 1, "Strength Sculpt", "Strength Training", "Build muscle and increase stamina with guided strength plans." },
                    { 2, "Cardio Burn", "Cardio & Endurance", "Maximize heart health and burn calories anywhere." },
                    { 3, "Yoga Flow", "Yoga & Flexibility", "Achieve mental clarity and body flexibility on the go." },
                    { 4, "Hotel Gym Ready", "Minimal Equipment", "Compact, equipment-light plans perfect for hotel gyms." },
                    { 5, "HIIT Blast", "High-Intensity Interval Training", "Short, intense bursts to maximize calorie burn." },
                    { 6, "Outdoor Athlete", "Bodyweight & Outdoor", "Bodyweight training designed for outdoor spaces." },
                    { 7, "Zen & Recover", "Stretch & Relaxation", "Active recovery and stretching to prevent injury." },
                    { 8, "Power Athlete", "Advanced Strength", "Advanced strength training for experienced lifters." },
                    { 9, "Functional Move", "Functional Fitness", "Functional movement patterns for everyday strength." }
                });

            // Advance the identity sequence past the explicit ids inserted above.
            migrationBuilder.Sql("SELECT setval(pg_get_serial_sequence('\"Workouts\"', 'Id'), (SELECT MAX(\"Id\") FROM \"Workouts\"));");

            migrationBuilder.AddColumn<int>(
                name: "WorkoutId",
                table: "TimetableSlots",
                type: "integer",
                nullable: false,
                defaultValue: 1);

            migrationBuilder.CreateIndex(
                name: "IX_TimetableSlots_WorkoutId",
                table: "TimetableSlots",
                column: "WorkoutId");

            migrationBuilder.AddForeignKey(
                name: "FK_TimetableSlots_Workouts_WorkoutId",
                table: "TimetableSlots",
                column: "WorkoutId",
                principalTable: "Workouts",
                principalColumn: "Id",
                onDelete: ReferentialAction.Restrict);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_TimetableSlots_Workouts_WorkoutId",
                table: "TimetableSlots");

            migrationBuilder.DropTable(
                name: "Workouts");

            migrationBuilder.DropIndex(
                name: "IX_TimetableSlots_WorkoutId",
                table: "TimetableSlots");

            migrationBuilder.DropColumn(
                name: "WorkoutId",
                table: "TimetableSlots");
        }
    }
}
