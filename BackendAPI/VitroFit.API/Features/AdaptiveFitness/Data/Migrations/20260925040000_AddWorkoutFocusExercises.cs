using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace VitroFit.API.Features.AdaptiveFitness;

[DbContext(typeof(FitnessDbContext))]
[Migration("20260925040000_AddWorkoutFocusExercises")]
public sealed class AddWorkoutFocusExercises : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.UpdateData(
            schema: "fitness",
            table: "Exercises",
            keyColumn: "Id",
            keyValue: 2,
            column: "MuscleGroup",
            value: "chest");

        migrationBuilder.InsertData(
            schema: "fitness",
            table: "Exercises",
            columns: ["Id", "BeginnerAllowed", "Equipment", "Instructions", "MuscleGroup", "Name"],
            values: new object[,]
            {
                { 8, true, "bodyweight", "Keep elbows close to your sides and press gently away from the wall.", "triceps", "Close-grip wall push-up" },
            });

        migrationBuilder.InsertData(
            schema: "fitness",
            table: "Exercises",
            columns: ["Id", "BeginnerAllowed", "Equipment", "Instructions", "MuscleGroup", "Name"],
            values: new object[,]
            {
                { 9, true, "bodyweight", "Stand facing a wall, place hands at chest height, and press with control.", "chest", "Wall chest press" },
                { 10, true, "resistance_band", "Use a secure band anchor and extend elbows without locking them.", "triceps", "Band triceps press-down" },
                { 11, true, "dumbbells", "Hinge slightly at the hips and raise light weights with control.", "back", "Seated reverse fly" },
                { 12, true, "bodyweight", "From hands and knees, extend opposite arm and leg while keeping the trunk steady.", "back", "Bird dog" },
                { 13, true, "bodyweight", "Push hips back with a neutral spine, then stand tall.", "legs", "Standing hip hinge" },
                { 14, true, "bodyweight", "Lie on your back, press through your feet, and lift hips comfortably.", "legs", "Glute bridge" },
                { 15, true, "bodyweight", "Hold a stable support and lower only through a comfortable range.", "legs", "Supported split squat" }
            });
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DeleteData(schema: "fitness", table: "Exercises", keyColumn: "Id", keyValue: 15);
        migrationBuilder.DeleteData(schema: "fitness", table: "Exercises", keyColumn: "Id", keyValue: 14);
        migrationBuilder.DeleteData(schema: "fitness", table: "Exercises", keyColumn: "Id", keyValue: 13);
        migrationBuilder.DeleteData(schema: "fitness", table: "Exercises", keyColumn: "Id", keyValue: 12);
        migrationBuilder.DeleteData(schema: "fitness", table: "Exercises", keyColumn: "Id", keyValue: 11);
        migrationBuilder.DeleteData(schema: "fitness", table: "Exercises", keyColumn: "Id", keyValue: 10);
        migrationBuilder.DeleteData(schema: "fitness", table: "Exercises", keyColumn: "Id", keyValue: 9);
        migrationBuilder.DeleteData(schema: "fitness", table: "Exercises", keyColumn: "Id", keyValue: 8);
        migrationBuilder.UpdateData(
            schema: "fitness",
            table: "Exercises",
            keyColumn: "Id",
            keyValue: 2,
            column: "MuscleGroup",
            value: "upper body");
    }
}
